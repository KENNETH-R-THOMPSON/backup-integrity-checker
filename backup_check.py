"""Create and verify portable SHA-256 manifests without changing source files."""
import argparse
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


def scan(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Source must be an existing directory, not a symbolic link')
    files = {}
    def fail(error):
        raise error
    for folder, dirs, names in os.walk(root, onerror=fail):
        for name in dirs + names:
            if (Path(folder) / name).is_symlink():
                raise ValueError('Symbolic links are not supported: ' + name)
        for name in sorted(names):
            path = Path(folder) / name
            if not path.is_file():
                raise ValueError('Only regular files are supported: ' + str(path))
            before = path.stat()
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                opened = os.fstat(stream.fileno())
                if not stat.S_ISREG(opened.st_mode) or file_identity(before) != file_identity(opened):
                    raise ValueError('File changed during scan: ' + str(path))
                # Stream large backups instead of loading entire files into memory.
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
                finished = os.fstat(stream.fileno())
            # Check both the open file and its path to detect edits or replacements.
            if file_identity(opened) != file_identity(finished) or file_identity(finished) != file_identity(path.stat()):
                raise ValueError('File changed during scan: ' + str(path))
            files[path.relative_to(root).as_posix()] = digest.hexdigest()
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
    parser.add_argument('--format', choices=['json', 'text'], default='json',
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
        report = compare(load_manifest(args.manifest), scan(args.directory))
        if args.format == 'json':
            print(json.dumps(report, indent=2))
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
