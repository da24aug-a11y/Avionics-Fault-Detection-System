// ================= GLOBAL =================
let pieChart;
let barChart;

// ================= PREDICT =================
async function predict() {
  const text = document.getElementById("incidentInput").value;

  if (!text.trim()) {
    alert("Please enter an incident description");
    return;
  }

  document.getElementById("faults").innerText = "Analyzing...";
  document.getElementById("confidenceList").innerHTML = "";
  document.getElementById("actionsList").innerHTML = "";
  document.getElementById("evidenceList").innerHTML = "";

  try {
    const res = await fetch("http://127.0.0.1:8000/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: text })
    });

    const data = await res.json();

    // ================= ERROR SAFE CHECK =================
    if (data.error) {
      alert("Backend error: " + data.error);
      return;
    }

    // ================= FAULTS =================
    document.getElementById("faults").innerText =
      (data.labels || []).join(", ");

    // ================= CONFIDENCE =================
    const confList = document.getElementById("confidenceList");
    confList.innerHTML = "";

    Object.entries(data.confidences || {}).forEach(([k, v]) => {
      const li = document.createElement("li");
      li.innerText = `${k}: ${v}%`;
      confList.appendChild(li);
    });

    // ================= ACTIONS =================
    const actionsList = document.getElementById("actionsList");
    actionsList.innerHTML = "";

    (data.actions || []).forEach(a => {
      const li = document.createElement("li");
      li.innerText = a;
      actionsList.appendChild(li);
    });

    // ================= EVIDENCE =================
    const evidenceList = document.getElementById("evidenceList");
    evidenceList.innerHTML = "";

    (data.evidence || []).forEach(e => {
      const li = document.createElement("li");
      li.innerText = `[${e.similarity}] ${e.summary.slice(0, 120)}...`;
      evidenceList.appendChild(li);
    });

    // ================= TABLE =================
    const table = document.querySelector("table");
    const row = table.insertRow(1);

    const date = new Date().toLocaleDateString();
    const fault = data.labels?.[0] || "Unknown";

    let severity = "Low";
    if ((data.labels || []).includes("Engine Failure")) severity = "Critical";
    else if ((data.labels || []).includes("Mechanical Failure")) severity = "High";
    else if ((data.labels || []).includes("Weather")) severity = "Medium";

    row.insertCell(0).innerText = date;
    row.insertCell(1).innerText = "N/A";
    row.insertCell(2).innerText = fault;
    row.insertCell(3).innerText = severity;

    // ================= PIE CHART =================
    if (pieChart) {
      const counts = {
        "Engine Failure": 0,
        "Weather": 0,
        "Human Error": 0,
        "Mechanical Failure": 0
      };

      (data.labels || []).forEach(l => {
        if (counts[l] !== undefined) {
          counts[l]++;
        }
      });

      pieChart.data.datasets[0].data = Object.values(counts);
      pieChart.update();
    }

    // ================= BAR CHART =================
    if (barChart) {
      let severityCounts = [0, 0, 0, 0];

      const labels = data.labels || [];

      labels.forEach(l => {
        if (l === "Engine Failure") severityCounts[3]++;
        else if (l === "Mechanical Failure") severityCounts[2]++;
        else if (l === "Weather") severityCounts[1]++;
        else severityCounts[0]++;
      });

      barChart.data.datasets[0].data = severityCounts;
      barChart.update();
    }

  } catch (err) {
    console.error(err);
    alert("Error connecting to backend");
  }
}

// ================= DASHBOARD CARDS =================
async function updateCards() {
  try {
    const res = await fetch("http://127.0.0.1:8000/dashboard");

    if (!res.ok) return;

    const data = await res.json();

    document.querySelector(".card:nth-child(1) p").innerText = (data.total ?? 0) + 15;
    document.querySelector(".card:nth-child(2) p").innerText = data.high_risk ?? 0;
    document.querySelector(".card:nth-child(3) p").innerText = data.common_fault ?? "None";
    document.querySelector(".card:nth-child(4) p").innerText = (data.accuracy ?? 0) + "%";

  } catch (err) {
    console.log("Dashboard error:", err);
  }
}

// ================= INIT =================
window.onload = function () {

  const pieCtx = document.getElementById("pieChart").getContext("2d");

  pieChart = new Chart(pieCtx, {
    type: "pie",
    data: {
      labels: ["Engine Failure", "Weather", "Human Error", "Mechanical Failure"],
      datasets: [{ data: [0, 0, 0, 0] }]
    }
  });

  const barCtx = document.getElementById("barChart").getContext("2d");

  barChart = new Chart(barCtx, {
    type: "bar",
    data: {
      labels: ["Low", "Medium", "High", "Critical"],
      datasets: [{ label: "Incidents", data: [0, 0, 0, 0] }]
    }
  });

  updateCards();
  setInterval(updateCards, 3000);
};