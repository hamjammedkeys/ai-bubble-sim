interface Props {
  shock: number;
  onShockChange: (value: number) => void;
  onRun: () => void;
}

export function ScenarioControls({ shock, onShockChange, onRun }: Props) {
  return (
    <section className="panel controls">
      <h2>Cloud AI Spending Slowdown</h2>
      <label>
        Shock
        <select value={shock} onChange={(event) => onShockChange(Number(event.target.value))}>
          <option value={0.2}>20%</option>
          <option value={0.3}>30%</option>
          <option value={0.4}>40%</option>
        </select>
      </label>
      <button type="button" onClick={onRun}>Run shock</button>
      <p className="assumption">Pass-through 80% · Propagation 50% · 3 rounds</p>
    </section>
  );
}
