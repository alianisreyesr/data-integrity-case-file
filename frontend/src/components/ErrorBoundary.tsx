import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { children: ReactNode };
type State = { hasError: boolean };

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo): void {
    // Keep technical details out of the portfolio UI.
  }

  tryAgain = (): void => {
    this.setState({ hasError: false });
  };

  reloadApplication = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <main className="main" role="alert" aria-labelledby="application-error-title">
          <section className="section">
            <h1 id="application-error-title">Something did not load correctly</h1>
            <p>
              Your information has not been changed. Try again first. If the issue continues, reload the
              application and confirm the local Docker services are running.
            </p>
            <div className="filters">
              <button type="button" className="primary" onClick={this.tryAgain}>
                Try again
              </button>
              <button type="button" className="link" onClick={this.reloadApplication}>
                Reload application
              </button>
            </div>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
