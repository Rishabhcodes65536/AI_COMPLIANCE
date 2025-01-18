document.addEventListener('DOMContentLoaded', () => {
    // Theme toggle functionality
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const htmlElement = document.documentElement;
    const logo = document.getElementById('logo');

    themeToggle.addEventListener('click', () => {
        if (htmlElement.classList.contains('dark')) {
            htmlElement.classList.remove('dark');
            themeIcon.classList.replace('fa-sun', 'fa-moon');
            logo.src = "/static/images/min_ai_logo.jpg";
        } else {
            htmlElement.classList.add('dark');
            themeIcon.classList.replace('fa-moon', 'fa-sun');
            logo.src = "/static/images/dark_logo.png";
        }
    });

    // Carousel functionality
    const carousel = document.querySelector('.testimonial-carousel .flex');
    let isDragging = false;
    let startX;
    let scrollLeft;
    let isAutoScrolling = true;
    let autoScrollInterval;

    // ...rest of the carousel code...

    // Initialize AOS
    AOS.init({
        duration: 1200,
        once: true,
        offset: 50
    });

    // Card animations
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            gsap.to(card, {
                rotationY: (x / rect.width - 0.5) * 20,
                rotationX: (y / rect.height - 0.5) * -20,
                duration: 0.3,
                ease: 'power1.out'
            });
        });

        card.addEventListener('mouseleave', () => {
            gsap.to(card, {
                rotationY: 0,
                rotationX: 0,
                duration: 0.3,
                ease: 'power1.out'
            });
        });
    });
});
