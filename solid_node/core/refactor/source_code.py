import os

class SourceCode:
    def __init__(self, source_path, interruption_line, interruption_args):
        self.path = source_path
        self.name = self.path.split('/')[-1].replace('.py', '')
        self.basedir = os.path.dirname(self.path)
        self.interruption = interruption_line

        # Get source code of file
        with open(self.path, 'r') as fh:
            self.source_code = fh.readlines()

        self.class_position = self._find_class_position()

        name, base = self._find_class_name_and_base()
        self.class_name = name
        self.class_base = base

        self.indent = self._get_interruption_indent()

        self.interruption_args = interruption_args
        self.interruption_kwargs = self._get_interruption_kwargs()
        self.arg_names = list(self.interruption_kwargs.keys())

        self.sections = {
            'imports': [],
            'pre_class': [],
            'class_declaration': [],
            'pre_interruption': [],
            'interruption': [],
            'post_interruption': []
        }

        self._fill_sections()

    def get(self, section):
        return self.sections[section][:]

    def _fill_sections(self):
        end_imports = False
        for (i, line) in enumerate(self.source_code):
            if not end_imports and len(line.strip()) > 0 and 'import' not in line:
                end_imports = True
                imports = self.sections['imports']
                pre_class = self.sections['pre_class']
                while imports and not imports[-1].strip():
                    pre_class.append(imports.pop())
            if not end_imports:
                section = 'imports'
            elif i < self.class_position:
                section = 'pre_class'
            elif i == self.class_position:
                section = 'class_declaration'
            elif i < self.interruption:
                section = 'pre_interruption'
            elif i == self.interruption:
                section = 'interruption'
            else:
                section = 'post_interruption'

            self.sections[section].append(line)


    def _find_class_position(self):
        pos = None
        for i in range(self.interruption):
            line = self.source_code[i]
            if line.strip().startswith('class '):
                pos = i

        assert pos is not None
        return pos

    def _find_class_name_and_base(self):
        class_line = self.source_code[self.class_position]
        while ' (' in class_line:
            class_line = class_line.replace(' (', '(')

        class_dec = class_line.strip().split(' ')[1].strip()
        assert '(' in class_dec

        # The name of the class, and the base classes
        name = class_dec.split(':')[0].split('(')[0]
        base = class_dec.split('(')[1].split(')')[0]

        return name, base

    def _get_interruption_indent(self):
        # Get line indentation
        line = self.source_code[self.interruption]
        count = 0
        for char in line:
            if char == ' ':
                count += 1
            else:
                return ' ' * count

    def _get_interruption_kwargs(self):
        # Convert parameters to dictionary using context variable names
        line = self.source_code[self.interruption]
        cmd = line.strip()
        cmd = cmd.replace('raise ', '').strip()
        cmd = cmd[cmd.index('('):]  # remove class name
        names = cmd[1:-1]  # remove parenthesis
        names = [ name.strip() for name in names.split(',') ]

        return dict(zip(names, self.interruption_args))
