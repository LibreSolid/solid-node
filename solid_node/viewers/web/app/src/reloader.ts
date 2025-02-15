
type SetErrorType = React.Dispatch<React.SetStateAction<string>>;

export interface BuildError {
  error: string;
  tstamp: number;
}

export class Reloader {

  reloadTrigger: WebSocket | undefined;
  time: number;
  reload: () => void;

  setError: SetErrorType;
  errorTstamp: number | null = null;

  firstCheck: boolean;

  constructor(
    setError: SetErrorType,
    reload: () => void,
  ) {
    this.setError = setError;
    this.reload = reload;

    this.time = 0;

    this.firstCheck = true;

    this.watch();
  }

  watch() {
    const parts = window.location.href.split('/');
    const protocol = parts[0].replace('http', 'ws');
    const domain = parts[2];

    if (this.reloadTrigger) return;

    this.reloadTrigger = new WebSocket(`${protocol}//${domain}/ws/reload`);

    this.reloadTrigger.onmessage = (event) => {
      if (event.data === "reload") {
        this.checkBuild();
      }
    };

    this.reloadTrigger.onclose = () => {
      this.reloadTrigger = undefined;
      this.watch();
    };

  }

  async checkBuild() {
    const response = await fetch('/_build_error');
    const result = await response.json() as BuildError;
    if (!result.error || result.tstamp == this.errorTstamp) {
      this.setError('');
      this.reload();
    } else {
      this.errorTstamp = result.tstamp;
      this.setError(result.error);
    }
  }

}
