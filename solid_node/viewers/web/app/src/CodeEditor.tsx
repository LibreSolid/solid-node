import AceEditor from 'react-ace';
import { NodeLoader } from './loader';
import { useLocation } from 'react-router-dom';

import "ace-builds/src-noconflict/mode-python";
import "ace-builds/src-noconflict/theme-github";
import "ace-builds/src-noconflict/ext-language_tools";

type CodeEditorProps = {
  loader: NodeLoader | undefined;
}

const CodeEditor = (props: CodeEditorProps) => {
  const location = useLocation();

  return (
    <div>
      <AceEditor
        mode="python"
        theme="github"
        value={props.loader?.code}
        onChange={props.loader?.setCode}
        name="code-editor"
        editorProps={{ $blockScrolling: true }}
      ></AceEditor>
    </div>
  );
};

export default CodeEditor
