console.log("🚀 Nexora OS V9 Online");

/* PARTICLES */

const particles = document.querySelector(".particles");

if (particles) {
    for(let i = 0; i < 80; i++){
        const particle = document.createElement("span");

        particle.style.left = Math.random() * 100 + "vw";
        particle.style.animationDuration = (Math.random() * 10 + 5) + "s";
        particle.style.opacity = Math.random();
        particle.style.width = particle.style.height = (Math.random() * 6 + 2) + "px";

        particles.appendChild(particle);
    }
}

/* PROJECT FILTERS */

const searchProject = document.querySelector("#searchProject");
const filterStatus = document.querySelector("#filterStatus");
const searchableCards = document.querySelectorAll(".searchable");

function filterProjects(){
    const search = searchProject?.value.toLowerCase() || "";
    const status = filterStatus?.value || "todos";

    searchableCards.forEach(card => {
        const title = card.dataset.title.toLowerCase();
        const cardStatus = card.dataset.status;

        const matchSearch = title.includes(search);
        const matchStatus = status === "todos" || cardStatus === status;

        card.style.display = matchSearch && matchStatus ? "block" : "none";
    });
}

searchProject?.addEventListener("input", filterProjects);
filterStatus?.addEventListener("change", filterProjects);

/* DRAG & DROP KANBAN */

const tasks = document.querySelectorAll(".kanban-task");
const columns = document.querySelectorAll(".kanban-column");

let draggedTask = null;

tasks.forEach(task => {
    task.addEventListener("dragstart", () => {
        draggedTask = task;
        task.classList.add("dragging");
    });

    task.addEventListener("dragend", () => {
        task.classList.remove("dragging");
    });
});

columns.forEach(column => {
    column.addEventListener("dragover", e => {
        e.preventDefault();
        column.classList.add("drag-over");
    });

    column.addEventListener("dragleave", () => {
        column.classList.remove("drag-over");
    });

    column.addEventListener("drop", () => {
        column.classList.remove("drag-over");

        if (draggedTask) {
            column.appendChild(draggedTask);

            const tareaId = draggedTask.dataset.id;
            const nuevoEstado = column.dataset.status;

            fetch("/api/tarea/estado", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    tarea_id: tareaId,
                    estado: nuevoEstado
                })
            });
        }
    });
});