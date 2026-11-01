"""Create and verify portable SHA-256 manifests without changing source files."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile


def file_identity(info):
    """Metadata used to notice files changing while they are being hashed."""
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def is_link_or_reparse(info):
    """Reject symlinks and Windows reparse points, including junctions."""
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, 'st_file_attributes', 0)
        & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)
    )


def scan(root):
    root = Path(root)
    root_before = root.stat(follow_symlinks=False)
    if not stat.S_ISDIR(root_before.st_mode) or is_link_or_reparse(root_before):
        raise ValueError('Source must be an existing directory, not a link or junction')
    files = {}
    # Remember each child directory seen by a path-based walk so a replacement
    # between listing the parent and entering the child is noticed.
    directory_identities = {root: file_identity(root_before)}
    def fail(error):
        raise error
    # On Unix, keep each directory open while reading its children.
    # This prevents a renamed parent directory from redirecting file opens.
    use_dir_fd = hasattr(os, 'fwalk') and hasattr(os, 'O_NOFOLLOW')
    if use_dir_fd:
        folders = os.fwalk(root, onerror=fail, follow_symlinks=False)
    else:
        folders = ((folder, dirs, names, None)
                   for folder, dirs, names in os.walk(root, onerror=fail))
    for folder, dirs, names, folder_fd in folders:
        folder_before = (os.fstat(folder_fd) if folder_fd is not None
                         else Path(folder).stat(follow_symlinks=False))
        if (not stat.S_ISDIR(folder_before.st_mode) or is_link_or_reparse(folder_before)
                or (folder_fd is None and
                    file_identity(folder_before) != directory_identities.get(Path(folder)))):
            raise ValueError('Directory changed during scan: ' + str(folder))
        for name in dirs + names:
            if folder_fd is not None:
                entry = os.stat(name, dir_fd=folder_fd, follow_symlinks=False)
            else:
                entry = (Path(folder) / name).stat(follow_symlinks=False)
            if is_link_or_reparse(entry):
                raise ValueError('Links and junctions are not supported: ' + name)
            if folder_fd is None and name in dirs:
                directory_identities[Path(folder) / name] = file_identity(entry)
        for name in sorted(names):
            path = Path(folder) / name
            if folder_fd is not None:
                before = os.stat(name, dir_fd=folder_fd, follow_symlinks=False)
            else:
                before = path.stat(follow_symlinks=False)
            if is_link_or_reparse(before):
                raise ValueError('Links and junctions are not supported: ' + str(path))
            if not stat.S_ISREG(before.st_mode):
                raise ValueError('Only regular files are supported: ' + str(path))
            digest = hashlib.sha256()
            # Refuse a symlink swapped in after the directory walk checked it.
            # O_NOFOLLOW is available on Linux and macOS. Other platforms still
            # use the before/after identity checks, but cannot close this race.
            flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0)
            flags |= getattr(os, 'O_NOFOLLOW', 0)
            flags |= getattr(os, 'O_NONBLOCK', 0)
            if folder_fd is not None:
                descriptor = os.open(name, flags, dir_fd=folder_fd)
            else:
                descriptor = os.open(path, flags)
            with os.fdopen(descriptor, 'rb') as stream:
                opened = os.fstat(stream.fileno())
                if not stat.S_ISREG(opened.st_mode) or file_identity(before) != file_identity(opened):
                    raise ValueError('File changed during scan: ' + str(path))
                # Stream large backups instead of loading entire files into memory.
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
                finished = os.fstat(stream.fileno())
            # Check both the open file and its path to detect edits or replacements.
            if folder_fd is not None:
                after = os.stat(name, dir_fd=folder_fd, follow_symlinks=False)
            else:
                after = path.stat(follow_symlinks=False)
            if file_identity(opened) != file_identity(finished) or file_identity(finished) != file_identity(after):
                raise ValueError('File changed during scan: ' + str(path))
            files[path.relative_to(root).as_posix()] = digest.hexdigest()
        # Check the folder again after its files, including on Windows where
        # descriptor-based directory walking is unavailable.
        if file_identity(folder_before) != file_identity(os.stat(folder, follow_symlinks=False)):
            raise ValueError('Directory changed during scan: ' + str(folder))
    if file_identity(root_before) != file_identity(root.stat(follow_symlinks=False)):
        raise ValueError('Source directory changed during scan: ' + str(root))
    return dict(sorted(files.items()))


def reject_duplicate_keys(pairs):
    """Reject JSON objects whose repeated keys could hide manifest entries."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate manifest key: ' + key)
        result[key] = value
    return result


def load_manifest(path):
    data = json.loads(
        Path(path).read_text(encoding='utf-8'),
        object_pairs_hook=reject_duplicate_keys,
    )
    if (not isinstance(data, dict) or type(data.get('version')) is not int
            or data['version'] != 1 or data.get('algorithm') != 'sha256'):
        raise ValueError('Unsupported manifest format')
    files = data.get('files')
    if not isinstance(files, dict):
        raise ValueError('Manifest files must be an object')
    for name, digest in files.items():
        relative = PurePosixPath(name)
        if (not name or relative.is_absolute() or '..' in relative.parts
                or relative.as_posix() != name or name == '.' or '\\' in name):
            raise ValueError('Invalid manifest path: ' + name)
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Invalid SHA-256 digest: ' + name)
    return files


def compare(expected, actual):
    return {
        'missing': sorted(expected.keys() - actual.keys()),
        'unexpected': sorted(actual.keys() - expected.keys()),
        'changed': sorted(name for name in expected.keys() & actual.keys() if expected[name] != actual[name]),
        'unchanged': sum(expected[name] == actual[name] for name in expected.keys() & actual.keys()),
    }


def spreadsheet_safe_name(name):
    """Keep a filename from being interpreted as a formula in a CSV viewer."""
    if name.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + name
    return name


def write_manifest(path, data):
    """Publish a complete baseline without replacing an existing one.

    A temporary file is written in the target directory, then linked to the
    final name using an exclusive filesystem operation. This needs hard-link
    support on the destination filesystem.
    """
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=path.parent,
            prefix='.' + path.name + '.', suffix='.tmp', delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # Fails if the baseline already exists.
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['snapshot', 'verify'])
    parser.add_argument('directory', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--format', choices=['json', 'text', 'csv'], default='json',
                        help='Verification report format (default: json)')
    args = parser.parse_args(argv)
    try:
        root, manifest = args.directory.resolve(), args.manifest.resolve()
        if root == manifest or root in manifest.parents:
            raise ValueError('Keep the manifest outside the source directory')
        if args.command == 'snapshot':
            data = {'version': 1, 'algorithm': 'sha256', 'files': scan(args.directory)}
            write_manifest(args.manifest, data)
            print('Recorded {} files'.format(len(data['files'])))
            return 0
        expected = load_manifest(args.manifest)
        actual = scan(args.directory)
        report = compare(expected, actual)
        if args.format == 'json':
            print(json.dumps(report, indent=2))
        elif args.format == 'csv':
            writer = csv.writer(sys.stdout, lineterminator='\n')
            writer.writerow(['status', 'path'])
            for category in ('changed', 'missing', 'unexpected'):
                for name in report[category]:
                    writer.writerow([category, spreadsheet_safe_name(name)])
            for name in sorted(expected.keys() & actual.keys()):
                if expected[name] == actual[name]:
                    writer.writerow(['unchanged', spreadsheet_safe_name(name)])
        else:
            print('Backup verification report')
            print('Unchanged files: {}'.format(report['unchanged']))
            for category in ('changed', 'missing', 'unexpected'):
                print('{}: {}'.format(category.title(), len(report[category])))
                for name in report[category]:
                    # Escape control characters so filenames cannot forge report lines.
                    print('  ' + json.dumps(name, ensure_ascii=False))
        return int(any(report[key] for key in ('missing', 'unexpected', 'changed')))
    except (OSError, ValueError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
