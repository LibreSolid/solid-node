import React, { useRef, useEffect } from 'react';
import AceEditor from 'react-ace';
import { IAceEditor } from 'react-ace/lib/types';
import { Node } from './node';
import { useLocation } from 'react-router-dom';

import "ace-builds/src-noconflict/mode-python";
import "ace-builds/src-noconflict/theme-github";
import "ace-builds/src-noconflict/theme-crimson_editor";
import "ace-builds/src-noconflict/theme-monokai";
import "ace-builds/src-noconflict/ext-language_tools";
import "ace-builds/src-noconflict/keybinding-emacs";

type CodeEditorProps = {
  node: Node | undefined;
  fontSize: number;
}

const CodeEditor = (props: CodeEditorProps) => {
  const aceEditorRef = useRef<AceEditor>(null);
  const location = useLocation();


  useEffect(() => {
    console.log('changed');
    if (aceEditorRef.current && props.node) {
      const saveFile = () => {
        props.node?.saveCode();
      };

      const editor: IAceEditor = aceEditorRef.current.editor;
      editor.commands.addCommand({
        name: "saveFile",
        bindKey: { win: "Ctrl-S", mac: "Cmd-S" },
        exec: saveFile
      });
    }
  }, [aceEditorRef.current, props.node]);

  return (
    <div>
      <AceEditor
        ref={aceEditorRef}
        mode="python"
        theme="monokai"
        value={props.node?.newCode}
        onChange={(code) => props.node?.setCode(code)}
        name="code-editor"
        fontSize={16}
        editorProps={{ $blockScrolling: true }}
        wrapEnabled={true}
        keyboardHandler="emacs"
        style={{
          width: 'calc(100% - 2px)',
          overflow: 'hidden',
        }}
      ></AceEditor>
    </div>
  );
};

export default CodeEditor
