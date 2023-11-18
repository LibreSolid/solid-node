import AceEditor from 'react-ace';
import { NodeLoader } from './loader';
import { useLocation } from 'react-router-dom';

import "ace-builds/src-noconflict/mode-python";
import "ace-builds/src-noconflict/theme-github";
import "ace-builds/src-noconflict/theme-crimson_editor";
import "ace-builds/src-noconflict/ext-language_tools";

type CodeEditorProps = {
  loader: NodeLoader | undefined;
  fontSize: number;
}

const CodeEditor = (props: CodeEditorProps) => {
  const location = useLocation();

  return (
    <div>
      <AceEditor
        mode="python"
        theme="crimson_editor"
        value={props.loader?.code}
        onChange={props.loader?.setCodi}
        name="code-editor"
        fontSize={16}
        editorProps={{ $blockScrolling: true }}
        wrapEnabled={true}
        style={{
          width: 'calc(100% - 2px)',
          overflow: 'hidden',
        }}
      ></AceEditor>
    </div>
  );
};

export default CodeEditor
