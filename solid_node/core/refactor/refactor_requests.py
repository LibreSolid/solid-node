import os
import sys
import logging
import inspect
from solid_node.core.refactor.source_code import SourceCode
from solid_node.node import AssemblyNode
from solid_node.core.git import GitRepo

logger = logging.getLogger('core.refactor')


class RefactorRequest(Exception):
    def __init__(self, *args):
        frame = inspect.currentframe().f_back

        # Get file path where exception was raised
        self.path = frame.f_code.co_filename
        self.basedir = os.path.dirname(self.path)
        # Repo is already locked by builder
        self.repo = GitRepo(self.path)

        while self.path == __file__:
            frame = frame.f_back
            self.path = frame.f_code.co_filename

        self.source = SourceCode(self.path, frame.f_lineno - 1, args)

    def make_import(self, cls):
        module_name = inspect.getmodule(cls).__name__
        class_name = cls.__name__
        return f"from {module_name} import {class_name}"

    @property
    def arg_names(self):
        return self.source.arg_names


class EvolveAssembly(RefactorRequest):

    def refactor(self):
        with self.repo.sync_lock('EvolveAssembly'):
            new_classes = {}
            for child in self.arg_names:
                class_name = self.write_child(child)
                new_classes[child] = class_name

            self.write_internal(new_classes)

            children_list = self._children_names()
            from solid_node.core.loader import load_node
            node = load_node(self.path)

            self.repo.add(self.path)
            self.repo.commit(f'Refactor {node.name} into Assembly of {children_list}')

    def write_internal(self, new_classes):
        code = [
            f'from .{module} import {Klass}'
            for (module, Klass) in new_classes.items()
        ]

        code += [
            self.make_import(AssemblyNode), '\n'
            f'class {self.source.class_name}(AssemblyNode):'
        ]

        for name, class_name in new_classes.items():
            code += [
                f'    {name} = {class_name}()'
            ]
        code.append('')

        code += [
            f'    def render(self):\n',
            f'        return [',
        ]
        for name in new_classes.keys():
            code += [
                f'            self.{name},'
            ]
        code += '        ]',

        code = '\n'.join(code)

        remaining = [ comment_line(line)
                      for line in self.source.get('post_interruption')
                     ]

        with open(self.path, 'w') as fh:
            fh.write(code)

    def write_child(self, name):
        code = self.source.get('imports')
        code += self.source.get('pre_class')

        # Change class name and append class header
        class_line = self.source.get('class_declaration')[0]
        class_name = variable_to_class(name)
        class_line = class_line.replace(self.source.class_name, class_name)
        code.append(class_line)

        # Append code until refactor request
        code += self.source.get('pre_interruption')

        # Return this one node
        code.append(f'        return {name}\n')

        path = os.path.join(self.basedir, f'{name}.py')
        assert not os.path.exists(path)
        with open(path, 'w') as fh:
            fh.write(''.join(code))

        self.repo.add(path)

        return class_name

    def _children_names(self):
        if len(self.arg_names) == 1:
            self.arg_names[0]

        children_dsc = ', '.join(self.arg_names[:-1])
        return f'{children_dsc} and {self.arg_names[-1]}'


def comment_line(line):
    # Find the index of the first non-whitespace character
    first_non_whitespace = len(line) - len(line.lstrip())

    # Insert the comment symbol ('# ') after the initial whitespace
    commented_line = line[:first_non_whitespace] + '# ' + line[first_non_whitespace:]

    return commented_line


def variable_to_class(snake_str):
    components = snake_str.split('_')
    return ''.join(x.title() for x in components)
