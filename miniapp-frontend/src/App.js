import React, { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [multiplier, setMultiplier] = useState(1.0);
  const [flying, setFlying] = useState(false);
  const [cashedOut, setCashedOut] = useState(false);
  const [balance, setBalance] = useState(100);
  const [bet, setBet] = useState(10);

  useEffect(() => {
    let interval;
    if (flying && !cashedOut) {
      interval = setInterval(() => {
        setMultiplier((prev) => parseFloat((prev + Math.random() * 0.1).toFixed(2)));
      }, 500);
    }
    return () => clearInterval(interval);
  }, [flying, cashedOut]);

  const startGame = () => {
    setMultiplier(1.0);
    setFlying(true);
    setCashedOut(false);

    setTimeout(() => {
      if (!cashedOut) {
        setFlying(false);
        alert("💥 Plane crashed at x" + multiplier);
      }
    }, Math.random() * 5000 + 2000); // crash between 2–7 sec
  };

  const cashOut = () => {
    if (flying && !cashedOut) {
      const winnings = bet * multiplier;
      setBalance(balance + winnings);
      setCashedOut(true);
      setFlying(false);
      alert("✅ You cashed out at x" + multiplier + "! Won: " + winnings);
    }
  };

  return (
    <div className="App">
      <h1>✈️ Aviator Mini Game</h1>
      <p>Balance: {balance} coins</p>
      <p>Bet: {bet} coins</p>
      <p>Multiplier: x{multiplier}</p>

      {!flying ? (
        <button onClick={startGame} className="start-btn">Fly 🚀</button>
      ) : (
        <button onClick={cashOut} className="cashout-btn">Cash Out 💰</button>
      )}
    </div>
  );
}

export default App;
