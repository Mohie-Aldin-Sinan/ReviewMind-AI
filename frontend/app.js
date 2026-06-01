const priorityItems = [
  {
    title: "Fix checkout crash on low-memory devices",
    description:
      "Android users repeatedly report app crashes after tapping Pay Now, especially on older devices.",
    score: 86,
  },
  {
    title: "Reduce onboarding friction",
    description:
      "New users mention confusion around account setup, permissions, and first-time navigation.",
    score: 72,
  },
  {
    title: "Improve notification controls",
    description:
      "Power users want clearer controls for push frequency, reminders, and promotional alerts.",
    score: 58,
  },
];

const clusters = [
  {
    title: "Reliability",
    description:
      "Crashes, freezes, slow loading, and failed actions that block users from completing core flows.",
    tags: ["High impact", "Bug", "Retention"],
    tone: "bad",
  },
  {
    title: "User Experience",
    description:
      "Repeated confusion around onboarding, navigation labels, permissions, and empty states.",
    tags: ["Medium effort", "UX", "Activation"],
    tone: "warn",
  },
  {
    title: "Feature Demand",
    description:
      "Requests for saved preferences, smarter alerts, export options, and improved personalization.",
    tags: ["Growth", "Feature", "Engagement"],
    tone: "",
  },
];

function renderPriorities() {
  const list = document.querySelector("#priorityList");

  list.innerHTML = priorityItems
    .map(
      (item, index) => `
        <article class="priority-item">
          <span class="priority-rank">${index + 1}</span>
          <div class="priority-copy">
            <h4>${item.title}</h4>
            <p>${item.description}</p>
          </div>
          <span class="priority-score">${item.score}</span>
        </article>
      `,
    )
    .join("");
}

function renderClusters() {
  const grid = document.querySelector("#clusterGrid");

  grid.innerHTML = clusters
    .map(
      (cluster) => `
        <article class="cluster-card">
          <h4>${cluster.title}</h4>
          <p>${cluster.description}</p>
          <div class="cluster-meta">
            ${cluster.tags.map((tag) => `<span class="tag ${cluster.tone}">${tag}</span>`).join("")}
          </div>
        </article>
      `,
    )
    .join("");
}

renderPriorities();
renderClusters();
