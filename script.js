export default {
  async fetch(request, env, ctx) {
    // 1. ടൂളിൽ നിന്നുള്ള POST റിക്വസ്റ്റ് ആണെങ്കിൽ അത് ഹാൻഡിൽ ചെയ്യുന്നു
    if (request.method === 'POST') {
      try {
        const data = await request.json();
        
        return new Response(JSON.stringify({
          success: true,
          message: "POST request received successfully!",
          data: data
        }), {
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (err) {
        return new Response(JSON.stringify({
          success: false,
          error: "Invalid JSON data"
        }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    // 2. സാധാരണ ബ്രൗസറിൽ തുറക്കുമ്പോൾ കാണിക്കുന്ന Availability Status HTML പേജ്
    const htmlContent = `<!DOCTYPE html>
<html lang="ml">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Availability Status</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0; min-height: 100vh; display: grid; place-items: center;
      padding: 20px; background: linear-gradient(135deg, #101827, #1e293b);
      font-family: system-ui, -apple-system, "Noto Sans Malayalam", sans-serif;
      color: #f8fafc;
    }
    .card {
      width: min(100%, 420px); padding: 34px 24px; text-align: center;
      background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.14);
      border-radius: 24px; box-shadow: 0 20px 60px rgba(0,0,0,.28);
    }
    .dot {
      display: inline-block; width: 12px; height: 12px; border-radius: 50%;
      margin-right: 8px; vertical-align: 1px; background: #ef4444;
    }
    h1 { font-size: 1.5rem; margin: 0 0 22px; }
    #status { font-size: 1.65rem; font-weight: 750; margin: 12px 0; }
    #message { color: #cbd5e1; line-height: 1.7; margin: 8px 0 22px; }
    .time { font-size: 1.05rem; font-variant-numeric: tabular-nums; color: #e2e8f0; }
    .hours { margin-top: 24px; padding-top: 18px; border-top: 1px solid rgba(255,255,255,.14); color: #cbd5e1; font-size: .95rem; }
    .available #status { color: #4ade80; }
    .available .dot { background: #22c55e; box-shadow: 0 0 12px #22c55e; }
    .offline #status { color: #f87171; }
  </style>
</head>
<body>
  <main class="card offline" id="card" aria-live="polite">
    <h1>ലഭ്യതാ സ്റ്റാറ്റസ്</h1>
    <div><span class="dot"></span><span id="status">സ്റ്റാറ്റസ് പരിശോധിക്കുന്നു...</span></div>
    <p id="message">ദയവായി കാത്തിരിക്കുക.</p>
    <div class="time" id="clock"></div>
    <div class="hours">ലഭ്യമായ സമയം: രാവിലെ 8:00 മുതൽ രാത്രി 9:30 വരെ<br>സമയമേഖല: ഇന്ത്യ (IST)</div>
  </main>

  <script>
    function updateStatus() {
      const now = new Date();
      const ist = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
      const minutes = ist.getHours() * 60 + ist.getMinutes();
      const start = 8 * 60;
      const end = 21 * 60 + 30;
      const available = minutes >= start && minutes < end;

      const card = document.getElementById("card");
      card.className = "card " + (available ? "available" : "offline");
      document.getElementById("status").textContent =
        available ? "ഇപ്പോൾ ലഭ്യമാണ്" : "ഇപ്പോൾ ലഭ്യമല്ല (Offline)";
      document.getElementById("message").textContent = available
        ? "ഇപ്പോൾ ബന്ധപ്പെടാവുന്നതാണ്."
        : "ഇപ്പോൾ ഓഫ്‌ലൈൻ ആണ്. രാവിലെ 8:00 മണിക്ക് വീണ്ടും ലഭ്യമാകും.";

      document.getElementById("clock").textContent =
        "ഇന്ത്യൻ സമയം: " + ist.toLocaleTimeString("en-IN", {
          hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: true
        });
    }
    updateStatus();
    setInterval(updateStatus, 1000);
  </script>
</body>
</html>`;

    return new Response(htmlContent, {
      headers: { 'Content-Type': 'text/html;charset=UTF-8' },
    });
  }
};
