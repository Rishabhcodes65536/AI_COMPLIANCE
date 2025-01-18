document.querySelectorAll(".card").forEach((card) => {
  card.addEventListener("mousemove", (e) => {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    gsap.to(card, {
      rotationY: (x / rect.width - 0.5) * 20,
      rotationX: (y / rect.height - 0.5) * -20,
      duration: 0.3,
      ease: "power1.out",
    });
  });

  card.addEventListener("mouseleave", () => {
    gsap.to(card, {
      rotationY: 0,
      rotationX: 0,
      duration: 0.3,
      ease: "power1.out",
    });
  });
});

document
  .getElementById("checkUpdateBtn")
  .addEventListener("click", async function () {
    const loading = document.getElementById("loading");
    const result = document.getElementById("result");

    // Show the loading indicator
    loading.classList.remove("hidden");
    result.textContent = "";

    try {
      // Simulate an API call
      const response = await fetch("/check-update"); // Replace with your actual API endpoint
      const data = await response.json();

      // Hide the loading indicator
      loading.classList.add("hidden");

      // Display the result
      if (data.success) {
        result.innerHTML = `<span class="text-green-600">✔️ ${data.message}</span>`;
      } else {
        result.innerHTML = `<span class="text-red-600">❌ ${data.message}</span>`;
      }
    } catch (error) {
      // Hide the loading indicator
      loading.classList.add("hidden");

      // Display error message
      result.innerHTML = `<span class="text-red-600">❌ Unable to check updates. Please try again later.</span>`;
    }
  });


document.addEventListener("DOMContentLoaded", () => {
  const carousel = document.querySelector(".testimonial-carousel .flex");
  let isDragging = false;
  let startX;
  let scrollLeft;
  let isAutoScrolling = true;
  let autoScrollInterval;

  // Smooth scroll function
  function smoothScroll() {
    if (!isAutoScrolling) return;

    const maxScrollLeft = carousel.scrollWidth - carousel.clientWidth;

    // If we've reached the end, reset to the beginning
    if (carousel.scrollLeft >= maxScrollLeft) {
      carousel.scrollLeft = 0;
    } else {
      // Smooth scroll by one card width
      const cardWidth = carousel.querySelector(".testimonial-item").offsetWidth;
      carousel.scrollBy({
        left: cardWidth + 24, // Include margin
        behavior: "smooth",
      });
    }
  }

  // Start auto-scrolling
  function startAutoScroll() {
    isAutoScrolling = true;
    autoScrollInterval = setInterval(smoothScroll, 3000); // Scroll every 3 seconds
  }

  // Stop auto-scrolling
  function stopAutoScroll() {
    isAutoScrolling = false;
    clearInterval(autoScrollInterval);
  }

  // Mouse down event for dragging
  carousel.addEventListener("mousedown", (e) => {
    isDragging = true;
    startX = e.pageX - carousel.offsetLeft;
    scrollLeft = carousel.scrollLeft;
    stopAutoScroll(); // Stop auto-scroll when user starts interacting
  });

  // Mouse leave event
  carousel.addEventListener("mouseleave", () => {
    isDragging = false;
    startAutoScroll(); // Resume auto-scroll
  });

  // Mouse up event
  carousel.addEventListener("mouseup", () => {
    isDragging = false;
    startAutoScroll(); // Resume auto-scroll
  });

  // Mouse move event for dragging
  carousel.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    e.preventDefault();
    const x = e.pageX - carousel.offsetLeft;
    const walk = (x - startX) * 2; // Multiply by 2 to increase drag sensitivity
    carousel.scrollLeft = scrollLeft - walk;
  });

  // Touch events for mobile support
  carousel.addEventListener("touchstart", (e) => {
    startX = e.touches[0].pageX - carousel.offsetLeft;
    scrollLeft = carousel.scrollLeft;
    stopAutoScroll();
  });

  carousel.addEventListener("touchmove", (e) => {
    const x = e.touches[0].pageX - carousel.offsetLeft;
    const walk = (x - startX) * 2;
    carousel.scrollLeft = scrollLeft - walk;
  });

  carousel.addEventListener("touchend", () => {
    startAutoScroll();
  });

  // Accessibility: Pause on focus
  carousel.addEventListener("focus", stopAutoScroll);
  carousel.addEventListener("blur", startAutoScroll);

  // Initialize auto-scroll
  startAutoScroll();

  // AOS Animation with custom duration
  AOS.init({
    duration: 1200,
    once: true,
    offset: 50,
  });
});

  AOS.init({
    duration: 1200,
    once: true,
  });

    // Scroll-to-Top Button Logic
    const scrollToTopButton = document.getElementById('scrollToTop');

    // Show/hide button on scroll
    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            scrollToTopButton.classList.add('show');
        } else {
            scrollToTopButton.classList.remove('show');
        }
    });

    // Smooth scroll to top on click
    scrollToTopButton.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });


        tailwind.config = {
          darkMode: "class",
};
        
         document.addEventListener("DOMContentLoaded", () => {
           const toggleBannerButton = document.getElementById("toggleBanner");
           const banner = document.getElementById("banner");
           let bannerVisible = false;

           toggleBannerButton.addEventListener("click", () => {
             bannerVisible = !bannerVisible;
             if (bannerVisible) {
               banner.classList.remove("hidden");
               toggleBannerButton
                 .querySelector("i")
                 .classList.replace("fa-arrow-up", "fa-arrow-down");
             } else {
               banner.classList.add("hidden");
               toggleBannerButton
                 .querySelector("i")
                 .classList.replace("fa-arrow-down", "fa-arrow-up");
             }
           });
         });

         