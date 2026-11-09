import { createRoot } from 'react-dom/client';
import { Component } from 'react';
import type { ReactNode } from 'react';
import App from './App';
import './styles.css';
import './collection.css';

class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed)
      return (
        <main className="fatal">
          <p className="eyebrow">tang you chi</p>
          <h1>手帳を開き直しましょう</h1>
          <p>画面を表示できませんでした。保存済みの記録は残っています。</p>
          <button className="button" onClick={() => window.location.reload()}>
            もう一度開く
          </button>
        </main>
      );
    return this.props.children;
  }
}

createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>,
);
