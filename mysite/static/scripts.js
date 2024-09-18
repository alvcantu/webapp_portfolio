
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
document.addEventListener("DOMContentLoaded", function () {
  const accordions = document.querySelectorAll(".accordion");

  accordions.forEach(button => {
    button.addEventListener("click", function () {
      this.classList.toggle("active");

      const panel = this.nextElementSibling;
      panel.classList.toggle("show");
    });
  });
});
