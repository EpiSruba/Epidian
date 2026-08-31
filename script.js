const menuButton = document.querySelector('.menu-button');
const navigation = document.querySelector('.main-nav');
const dropdown = document.querySelector('.nav-dropdown');
const dropdownButton = document.querySelector('.nav-dropdown-toggle');

menuButton.addEventListener('click', () => {
  const isOpen = navigation.classList.toggle('open');
  menuButton.setAttribute('aria-expanded', String(isOpen));
});

navigation.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
  navigation.classList.remove('open');
  menuButton.setAttribute('aria-expanded', 'false');
  dropdown.classList.remove('open');
  dropdownButton.setAttribute('aria-expanded', 'false');
}));

dropdownButton.addEventListener('click', () => {
  const isOpen = dropdown.classList.toggle('open');
  dropdownButton.setAttribute('aria-expanded', String(isOpen));
});

document.addEventListener('click', (event) => {
  if (!dropdown.contains(event.target)) {
    dropdown.classList.remove('open');
    dropdownButton.setAttribute('aria-expanded', 'false');
  }
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    dropdown.classList.remove('open');
    dropdownButton.setAttribute('aria-expanded', 'false');
    dropdownButton.focus();
  }
});

document.querySelector('#year').textContent = new Date().getFullYear();

const newsletterForm = document.querySelector('.newsletter form');
if (newsletterForm) {
  newsletterForm.addEventListener('submit', (event) => {
    event.preventDefault();
  });
}

const scrollToCurrentSection = () => {
  if (!window.location.hash) return;
  const target = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
  if (target) target.scrollIntoView({ block: 'start' });
};

window.addEventListener('load', () => {
  requestAnimationFrame(() => requestAnimationFrame(scrollToCurrentSection));
});

window.addEventListener('hashchange', scrollToCurrentSection);
