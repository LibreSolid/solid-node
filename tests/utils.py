import re

def format_codes(generated, expected):
    generated = re.sub('\/\/.+?\n', '', generated)
    generated = generated.strip()
    generated = generated.replace('\t', '    ').strip()
    first_line = expected.split('\n')[1]
    spaces = len(first_line) - len(first_line.strip())
    column = '\n' + ' ' * spaces

    expected = expected.replace(column, '\n').strip()

    return generated, expected
