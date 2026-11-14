"""Static standalone utility completion; never invoke an implementation/provider."""
import sys
from utility_commands import complete


def main(arguments=None):
    args = list(sys.argv[1:] if arguments is None else arguments)
    typed = args[:1] == ['--display-types']
    if typed:
        args.pop(0)
    if not args:
        return 0
    for kind, value, description in complete(args[0], args[1:]):
        row = [kind, value, description]
        if typed:
            row.append('option' if value.startswith('-') else 'value')
        if any(any(ord(c) < 32 or ord(c) == 127 for c in field) for field in row):
            continue
        print('\t'.join(row))
    return 0


if __name__ == '__main__':
    sys.exit(main())
