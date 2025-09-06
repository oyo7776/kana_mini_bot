// static/app.js
(async () => {
  const log = (t)=> { document.getElementById('log').textContent = t + "\n" + document.getElementById('log').textContent; };

  // Telegram WebApp object (exists when opened inside Telegram)
  const tg = window.Telegram?.WebApp;
  if (tg) tg.ready();

  // get init data (string) and unsafe user object
  const initData = tg?.initData; // signed string
  const unsafe = tg?.initDataUnsafe || {};
  const user = unsafe.user || {};
  const user_id = user.id;

  // send initData to backend to verify and get/create user
  const authResp = await fetch("/api/auth", {
    method: "POST",
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ init_data: initData, user_id: user_id })
  }).then(r=>r.json()).catch(e=>({error:String(e)}));

  if (authResp.error) {
    document.getElementById('user').textContent = "Auth failed: " + authResp.error;
    log("Auth failed: " + JSON.stringify(authResp));
    return;
  }

  document.getElementById('user').textContent = `Hello ${user.username || user.first_name || 'Player'} (ID: ${authResp.user_id})`;
  const userId = authResp.user_id;

  // set balance
  const setBalanceUI = (v) => { document.getElementById('balance').textContent = v; }

  setBalanceUI(authResp.balance || 0);

  // helper: refresh balance
  async function refreshBalance() {
    const res = await fetch("/api/get_balance", {
      method: "POST", headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ user_id: userId })
    }).then(r=>r.json());
    if (!res.error) setBalanceUI(res.balance);
  }

  // Bet button
  document.getElementById('btnBet').addEventListener('click', async ()=>{
    const amt = parseFloat(document.getElementById('betAmount').value || 0);
    if (!amt || amt <= 0) { alert("Enter bet amount"); return; }
    log(`Betting ${amt}...`);
    const res = await fetch("/api/bet", {
      method: "POST", headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ user_id: userId, amount: amt, game: "aviator" })
    }).then(r=>r.json());
    log("Result: " + JSON.stringify(res));
    if (!res.error) setBalanceUI(res.balance);
  });

  // Deposit
  document.getElementById('btnDeposit').addEventListener('click', async ()=>{
    const amt = parseFloat(document.getElementById('depositAmount').value || 0);
    const email = document.getElementById('depositEmail').value;
    if (!amt || !email) { alert("Provide amount and email"); return; }
    log("Initializing payment...");
    const res = await fetch("/api/init_payment", {
      method: "POST", headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ user_id: userId, amount: amt, email: email })
    }).then(r=>r.json());
    log("Chapa response: " + JSON.stringify(res));
    const url = res?.data?.checkout_url || res?.checkout_url;
    if (url) {
      // open external checkout inside Telegram client
      if (tg && tg.openExternalLink) tg.openExternalLink(url);
      else window.open(url, "_blank");
    } else {
      alert("Failed to initialize payment. See logs.");
    }
  });

  // Withdraw
  document.getElementById('btnWithdraw').addEventListener('click', async ()=>{
    const amt = parseFloat(document.getElementById('withdrawAmount').value || 0);
    const email = document.getElementById('withdrawEmail').value;
    if (!amt || !email) { alert("Provide amount and recipient email"); return; }
    const res = await fetch("/api/withdraw", {
      method: "POST", headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ user_id: userId, amount: amt, email: email })
    }).then(r=>r.json());
    log("Withdraw result: " + JSON.stringify(res));
    if (res.status === "success") setBalanceUI(res.balance);
    else alert("Withdraw failed, see logs or contact admin.");
  });

  // initial refresh periodically
  setInterval(refreshBalance, 25_000);
})();
