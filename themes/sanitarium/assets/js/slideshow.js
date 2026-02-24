// Image slideshow and lightbox functionality
// Loaded as type="module" only on pages with slideshows

// Debounce helper for resize handler
function debounce(fn, ms) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), ms);
    };
}

// Respect prefers-reduced-motion
const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
let prefersReducedMotion = motionQuery.matches;
motionQuery.addEventListener('change', (e) => { prefersReducedMotion = e.matches; });

function getTransition() {
    return prefersReducedMotion ? 'transform 0s' : 'transform 0.3s ease-out';
}

// Track all slideshow instances for resize handling
const slideshowInstances = [];

// Store lightbox navigation functions for the global keydown handler
const lightboxHandlers = new Map();

document.querySelectorAll('.slideshow-wrapper').forEach(wrapper => {
    const slideshow = wrapper.querySelector('.image-slideshow');
    const lightbox = wrapper.querySelector('.slideshow-lightbox');

    // ── Slideshow ──────────────────────────────────────────────

    const track = slideshow.querySelector('.slideshow-track');
    const slides = slideshow.querySelectorAll('.slideshow-slide');
    const indicators = slideshow.querySelectorAll('.slideshow-indicator');
    const prevButton = slideshow.querySelector('.slideshow-nav-prev');
    const nextButton = slideshow.querySelector('.slideshow-nav-next');
    const slideshowImages = slideshow.querySelector('.slideshow-images');
    const hasMultipleSlides = slides.length > 1;

    let currentSlide = 0;
    let isDragging = false;
    let startX = 0;
    let currentTranslate = 0;
    let animationID = null;

    function getPositionX(event) {
        return event.type.includes('mouse') ? event.clientX : event.touches[0].clientX;
    }

    function updateTrackPosition(immediate = false) {
        const slideWidth = slideshowImages.offsetWidth;
        const targetTranslate = -currentSlide * slideWidth + currentTranslate;

        if (immediate) {
            track.style.transition = 'none';
        } else {
            track.style.transition = getTransition();
        }

        track.style.transform = `translateX(${targetTranslate}px)`;
    }

    function goToSlide(index, immediate = false) {
        // Wrap around
        if (index < 0) index = slides.length - 1;
        if (index >= slides.length) index = 0;

        // Update active slide
        slides[currentSlide].classList.remove('active');
        slides[index].classList.add('active');

        // Update indicators
        if (hasMultipleSlides) {
            indicators[currentSlide].classList.remove('active');
            indicators[currentSlide].setAttribute('aria-pressed', 'false');
            indicators[index].classList.add('active');
            indicators[index].setAttribute('aria-pressed', 'true');
        }

        currentSlide = index;
        currentTranslate = 0;
        updateTrackPosition(immediate);
    }

    function nextSlide() {
        goToSlide(currentSlide + 1);
    }

    function prevSlide() {
        goToSlide(currentSlide - 1);
    }

    // Navigation button events (only present for multi-image slideshows)
    if (prevButton) {
        prevButton.addEventListener('click', prevSlide);
    }

    if (nextButton) {
        nextButton.addEventListener('click', nextSlide);
    }

    // Indicator click events
    indicators.forEach((indicator, index) => {
        indicator.addEventListener('click', () => {
            goToSlide(index);
        });
    });

    // Keyboard navigation (only for multi-image slideshows)
    if (hasMultipleSlides) {
        slideshow.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                prevSlide();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                nextSlide();
            }
        });
    }

    // Drag/touch handlers
    function onDragMove(event) {
        if (isDragging) {
            const currentPosition = getPositionX(event);
            currentTranslate = currentPosition - startX;
        }
    }

    function onDragEnd() {
        if (!isDragging) return;

        isDragging = false;
        cancelAnimationFrame(animationID);
        slideshowImages.style.cursor = 'grab';

        // Remove document-level listeners
        document.removeEventListener('mousemove', onDragMove);
        document.removeEventListener('mouseup', onDragEnd);

        const slideWidth = slideshowImages.offsetWidth;
        const movedBy = currentTranslate;
        const threshold = slideWidth * 0.2;

        if (Math.abs(movedBy) >= 5 && hasMultipleSlides) {
            // This was a swipe gesture
            if (Math.abs(movedBy) > threshold) {
                if (movedBy > 0) {
                    prevSlide();
                } else {
                    nextSlide();
                }
            } else {
                // Snap back to current slide
                currentTranslate = 0;
                updateTrackPosition();
            }
        } else {
            // Movement < 5px (or single image) — treat as a tap, open lightbox
            currentTranslate = 0;
            updateTrackPosition();
            openLightbox(currentSlide);
        }
    }

    function dragStart(event) {
        isDragging = true;
        startX = getPositionX(event);
        animationID = requestAnimationFrame(animation);
        slideshowImages.style.cursor = 'grabbing';

        // Register document-level listeners only during drag
        document.addEventListener('mousemove', onDragMove);
        document.addEventListener('mouseup', onDragEnd);
    }

    // Animation loop for live drag feedback
    function animation() {
        updateTrackPosition(true);
        if (isDragging) animationID = requestAnimationFrame(animation);
    }

    // Mouse events — only mousedown on the element; move/up added dynamically
    slideshowImages.addEventListener('mousedown', dragStart);

    // Touch events
    slideshowImages.addEventListener('touchstart', dragStart, { passive: true });
    slideshowImages.addEventListener('touchmove', onDragMove, { passive: true });
    slideshowImages.addEventListener('touchend', onDragEnd);

    // Prevent default image drag behavior
    slideshowImages.addEventListener('dragstart', (e) => e.preventDefault());

    // Click to focus for keyboard navigation
    slideshow.addEventListener('click', (e) => {
        // Don't steal focus from buttons
        if (e.target.closest('.slideshow-nav, .slideshow-indicator')) return;
        slideshow.focus();
    });

    // Initialize position
    goToSlide(0, true);

    // Register for resize handling
    slideshowInstances.push({ updateTrackPosition });

    // ── Lightbox ───────────────────────────────────────────────

    const lightboxTrack = lightbox.querySelector('.lightbox-track');
    const lightboxImagesEl = lightbox.querySelector('.lightbox-images');
    const lightboxIndicatorsContainer = lightbox.querySelector('.lightbox-indicators');
    const lightboxClose = lightbox.querySelector('.lightbox-close');
    const lightboxOverlay = lightbox.querySelector('.lightbox-overlay');
    const lightboxPrevBtn = lightbox.querySelector('.lightbox-nav-prev');
    const lightboxNextBtn = lightbox.querySelector('.lightbox-nav-next');

    // State scoped to THIS slideshow instance
    let imagesData = [];
    let lightboxIndicatorsList = [];
    let currentLightboxIndex = 0;
    let lbIsDragging = false;
    let lbStartX = 0;
    let lbCurrentTranslate = 0;
    let lbAnimationID = null;
    let isTrackBuilt = false;

    // Build array of images from THIS slideshow only
    slideshow.querySelectorAll('.slideshow-slide img').forEach(img => {
        imagesData.push({
            src: img.getAttribute('data-original') || img.src,
            alt: img.alt
        });
    });

    function openLightbox(index) {
        // Move lightbox to <body> to avoid stacking context issues from CSS ancestors
        // (e.g. transform/will-change on article elements breaking position:fixed)
        document.body.appendChild(lightbox);
        lightbox.classList.add('active');
        lightbox.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';

        buildLightboxTrack();

        requestAnimationFrame(() => {
            goToLightboxSlide(index, true);
            lightboxClose.focus();
        });
    }

    // Build lightbox track and indicators once on first open
    function buildLightboxTrack() {
        if (isTrackBuilt) return;

        // Build slides
        lightboxTrack.innerHTML = '';
        imagesData.forEach(imageData => {
            const slide = document.createElement('div');
            slide.className = 'lightbox-slide';

            const img = document.createElement('img');
            img.src = imageData.src;
            img.alt = imageData.alt;

            slide.appendChild(img);
            lightboxTrack.appendChild(slide);
        });

        // Build indicators
        if (lightboxIndicatorsContainer && imagesData.length > 1) {
            lightboxIndicatorsContainer.innerHTML = '';
            imagesData.forEach((_, index) => {
                const indicator = document.createElement('button');
                indicator.className = 'lightbox-indicator' + (index === 0 ? ' active' : '');
                indicator.setAttribute('data-slide', index);
                indicator.setAttribute('aria-label', `Image ${index + 1} of ${imagesData.length}`);
                indicator.setAttribute('aria-pressed', index === 0 ? 'true' : 'false');
                indicator.setAttribute('type', 'button');

                indicator.addEventListener('click', (e) => {
                    e.stopPropagation();
                    goToLightboxSlide(index);
                });

                lightboxIndicatorsList.push(indicator);
                lightboxIndicatorsContainer.appendChild(indicator);
            });
        }

        isTrackBuilt = true;
    }

    function lbGetPositionX(event) {
        return event.type.includes('mouse') ? event.clientX : event.touches[0].clientX;
    }

    function updateLightboxPosition(immediate = false) {
        const slideWidth = lightboxImagesEl.offsetWidth;
        const targetTranslate = -currentLightboxIndex * slideWidth + lbCurrentTranslate;

        if (immediate) {
            lightboxTrack.style.transition = 'none';
        } else {
            lightboxTrack.style.transition = getTransition();
        }

        lightboxTrack.style.transform = `translateX(${targetTranslate}px)`;
    }

    function goToLightboxSlide(index, immediate = false) {
        // Wrap around
        if (index < 0) index = imagesData.length - 1;
        if (index >= imagesData.length) index = 0;

        // Update indicators
        if (lightboxIndicatorsList.length > 0) {
            lightboxIndicatorsList[currentLightboxIndex].classList.remove('active');
            lightboxIndicatorsList[currentLightboxIndex].setAttribute('aria-pressed', 'false');
            lightboxIndicatorsList[index].classList.add('active');
            lightboxIndicatorsList[index].setAttribute('aria-pressed', 'true');
        }

        currentLightboxIndex = index;
        lbCurrentTranslate = 0;
        updateLightboxPosition(immediate);
    }

    function nextLightboxImage() {
        goToLightboxSlide(currentLightboxIndex + 1);
    }

    function prevLightboxImage() {
        goToLightboxSlide(currentLightboxIndex - 1);
    }

    // Close lightbox and sync back to slideshow
    function closeLightbox() {
        // Return focus to slideshow before hiding (avoids aria-hidden warning)
        slideshow.focus();
        lightbox.classList.remove('active');
        lightbox.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';

        // Sync the inline slideshow to whichever slide the user navigated to
        goToSlide(currentLightboxIndex, true);
    }

    // Navigation buttons
    if (lightboxPrevBtn) {
        lightboxPrevBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            prevLightboxImage();
        });
    }

    if (lightboxNextBtn) {
        lightboxNextBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            nextLightboxImage();
        });
    }

    lightboxClose.addEventListener('click', closeLightbox);
    lightboxOverlay.addEventListener('click', closeLightbox);

    // Register handlers for global keydown dispatch
    lightboxHandlers.set(lightbox, { close: closeLightbox, prev: prevLightboxImage, next: nextLightboxImage });

    // Drag/touch support
    function lbOnDragMove(event) {
        if (lbIsDragging) {
            const currentPosition = lbGetPositionX(event);
            lbCurrentTranslate = currentPosition - lbStartX;
        }
    }

    function lbOnDragEnd() {
        if (!lbIsDragging) return;

        lbIsDragging = false;
        cancelAnimationFrame(lbAnimationID);

        // Remove document-level listeners
        document.removeEventListener('mousemove', lbOnDragMove);
        document.removeEventListener('mouseup', lbOnDragEnd);

        const slideWidth = lightboxImagesEl.offsetWidth;
        const movedBy = lbCurrentTranslate;
        const threshold = slideWidth * 0.2;

        if (Math.abs(movedBy) > threshold) {
            if (movedBy > 0) {
                prevLightboxImage();
            } else {
                nextLightboxImage();
            }
        } else {
            // Snap back to current slide
            lbCurrentTranslate = 0;
            updateLightboxPosition();
        }
    }

    function lbDragStart(event) {
        if (!lightbox.classList.contains('active')) return;
        // Don't drag if clicking on buttons
        if (event.target.closest('.lightbox-controls')) return;

        lbIsDragging = true;
        lbStartX = lbGetPositionX(event);
        lbAnimationID = requestAnimationFrame(lbAnimation);

        // Register document-level listeners only during drag
        document.addEventListener('mousemove', lbOnDragMove);
        document.addEventListener('mouseup', lbOnDragEnd);
    }

    // Animation loop for live drag feedback
    function lbAnimation() {
        updateLightboxPosition(true);
        if (lbIsDragging) lbAnimationID = requestAnimationFrame(lbAnimation);
    }

    // Mouse events — only mousedown on the element; move/up added dynamically
    lightboxImagesEl.addEventListener('mousedown', lbDragStart);

    // Touch events
    lightboxImagesEl.addEventListener('touchstart', lbDragStart, { passive: true });
    lightboxImagesEl.addEventListener('touchmove', lbOnDragMove, { passive: true });
    lightboxImagesEl.addEventListener('touchend', lbOnDragEnd);

    // Prevent default image drag behavior in lightbox
    lightboxImagesEl.addEventListener('dragstart', (e) => e.preventDefault());

    // Register for resize handling
    slideshowInstances.push({ updateTrackPosition: updateLightboxPosition });
});

// Single global keydown handler for all lightboxes
document.addEventListener('keydown', (e) => {
    const activeLightbox = document.querySelector('.slideshow-lightbox.active');
    if (!activeLightbox) return;

    const handlers = lightboxHandlers.get(activeLightbox);
    if (!handlers) return;

    if (e.key === 'Escape') {
        handlers.close();
    } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handlers.prev();
    } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        handlers.next();
    }
});

// Resize handler — recalculate track positions for all slideshows and lightboxes
window.addEventListener('resize', debounce(() => {
    slideshowInstances.forEach(instance => {
        instance.updateTrackPosition(true);
    });
}, 150));
