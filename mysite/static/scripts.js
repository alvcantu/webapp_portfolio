
// Logic for sidebar sandwich menu

const menuToggle = document.querySelector('.menu-toggle');
const sidebar = document.querySelector('.sidebar');
const content = document.querySelector('.content');

menuToggle.addEventListener('click', () => {
  sidebar.classList.toggle('active');
  if (window.innerWidth > 768) {
    content.classList.toggle('active');
  }
});

// Close sidebar when clicking outside
document.addEventListener('click', (event) => {
  if (!sidebar.contains(event.target) && !menuToggle.contains(event.target)) {
    sidebar.classList.remove('active');
    if (window.innerWidth > 768) {
      content.classList.remove('active');
    }
  }
});

// Handle window resize
window.addEventListener('resize', () => {
  if (window.innerWidth <= 768) {
    content.classList.remove('active');
  } else if (sidebar.classList.contains('active')) {
    content.classList.add('active');
  }
});


// Logic for accordions
var acc = document.getElementsByClassName("accordion");
var i;

for (i = 0; i < acc.length; i++) {
  acc[i].addEventListener("click", function() {
    this.classList.toggle("active");
    var panel = this.nextElementSibling;
    if (panel.style.display === "block") {
      panel.style.display = "none";
      panel.style.maxHeight = null;
    } else {
      panel.style.display = "block"; // Ensures the panel is shown
      panel.style.maxHeight = panel.scrollHeight + "px"; // Expands the panel
    }
  });
}
