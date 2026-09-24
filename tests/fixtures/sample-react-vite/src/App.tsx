import React, { useState } from 'react';

export default function App() {
  const [count, setCount] = useState(0);

  return (
    <div className="container">
      <div className="card">
        <div className="badge">ZIREF DEPLOYED</div>
        <h1>Ziref Demo React Application</h1>
        <p className="subtitle">
          Built with React 18, Vite, and TypeScript. Sandboxed, built, and deployed by Ziref!
        </p>

        <div className="counter-box">
          <button onClick={() => setCount(c => c + 1)} className="btn">
            Click Counter: {count}
          </button>
        </div>

        <div className="features">
          <div className="feature-item">⚡ Instant Build</div>
          <div className="feature-item">🔒 Sandboxed Container</div>
          <div className="feature-item">📱 Android Ready</div>
        </div>
      </div>
    </div>
  );
}
