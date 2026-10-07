document.addEventListener('DOMContentLoaded', function () {

    /* =========================================================
       MOBILE NAVIGATION
    ========================================================= */

    const navButton = document.querySelector('.nav-toggle');
    const navigation = document.querySelector('.main-nav');

    if (navButton && navigation) {

        navButton.addEventListener('click', function () {
            const isOpen = navigation.classList.toggle('open');

            navButton.setAttribute(
                'aria-expanded',
                String(isOpen)
            );

            navButton.setAttribute(
                'aria-label',
                isOpen ? 'Close navigation' : 'Open navigation'
            );
        });

        navigation.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                navigation.classList.remove('open');

                navButton.setAttribute(
                    'aria-expanded',
                    'false'
                );

                navButton.setAttribute(
                    'aria-label',
                    'Open navigation'
                );
            });
        });

        /* Close mobile menu when clicking outside */
        document.addEventListener('click', function (event) {
            if (
                navigation.classList.contains('open') &&
                !navigation.contains(event.target) &&
                !navButton.contains(event.target)
            ) {
                navigation.classList.remove('open');

                navButton.setAttribute(
                    'aria-expanded',
                    'false'
                );

                navButton.setAttribute(
                    'aria-label',
                    'Open navigation'
                );
            }
        });

        /* Close menu when resizing back to desktop */
        window.addEventListener('resize', function () {
            if (window.innerWidth > 820) {
                navigation.classList.remove('open');
                navButton.setAttribute('aria-expanded', 'false');
                navButton.setAttribute('aria-label', 'Open navigation');
            }
        });
    }


    /* =========================================================
       SCROLL REVEAL ANIMATION
    ========================================================= */

    const revealItems = document.querySelectorAll('.reveal');

    if ('IntersectionObserver' in window) {

        const observer = new IntersectionObserver(
            function (entries) {

                entries.forEach(function (entry) {

                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                        observer.unobserve(entry.target);
                    }

                });

            },
            {
                threshold: 0.10,
                rootMargin: '0px 0px -30px 0px'
            }
        );

        revealItems.forEach(function (item) {
            observer.observe(item);
        });

    } else {

        revealItems.forEach(function (item) {
            item.classList.add('visible');
        });

    }


    /* =========================================================
       RETINAL IMAGE UPLOAD + PREVIEW
    ========================================================= */

    const uploadInput = document.getElementById('file');
    const previewBox = document.getElementById('preview-box');
    const imagePreview = document.getElementById('image-preview');
    const removeImage = document.getElementById('remove-image');
    const uploadBox = document.getElementById('upload-box');

    if (
        uploadInput &&
        previewBox &&
        imagePreview &&
        removeImage
    ) {

        uploadInput.addEventListener('change', function () {

            const file = this.files && this.files[0];

            if (!file) {
                clearImagePreview();
                return;
            }

            /* Frontend validation only.
               Flask backend validation remains unchanged. */

            const allowedTypes = [
                'image/jpeg',
                'image/png'
            ];

            if (!allowedTypes.includes(file.type)) {

                alert(
                    'Please select a JPG, JPEG, or PNG retinal image.'
                );

                clearImagePreview();
                return;
            }

            /* Prevent extremely large browser previews.
               This does NOT replace backend validation. */

            const maxPreviewSize = 15 * 1024 * 1024;

            if (file.size > maxPreviewSize) {

                alert(
                    'This image is too large for preview. Please choose an image below 15 MB.'
                );

                clearImagePreview();
                return;
            }

            const reader = new FileReader();

            reader.onload = function (event) {

                imagePreview.src = event.target.result;

                previewBox.hidden = false;
                removeImage.hidden = false;

                if (uploadBox) {
                    uploadBox.classList.add('has-image');
                }
            };

            reader.onerror = function () {

                alert(
                    'Unable to preview this image. Please try another file.'
                );

                clearImagePreview();
            };

            reader.readAsDataURL(file);
        });


        removeImage.addEventListener('click', function (event) {

            event.preventDefault();
            event.stopPropagation();

            clearImagePreview();

        });


        function clearImagePreview() {

            uploadInput.value = '';

            imagePreview.src = '';

            previewBox.hidden = true;
            removeImage.hidden = true;

            if (uploadBox) {
                uploadBox.classList.remove('has-image');
            }
        }
    }


    /* =========================================================
       DRAG AND DROP UPLOAD
       Works with the existing #file input.
       Does NOT change Flask form behaviour.
    ========================================================= */

    if (uploadBox && uploadInput) {

        ['dragenter', 'dragover'].forEach(function (eventName) {

            uploadBox.addEventListener(eventName, function (event) {

                event.preventDefault();
                event.stopPropagation();

                uploadBox.classList.add('drag-active');

            });

        });


        ['dragleave', 'drop'].forEach(function (eventName) {

            uploadBox.addEventListener(eventName, function (event) {

                event.preventDefault();
                event.stopPropagation();

                uploadBox.classList.remove('drag-active');

            });

        });


        uploadBox.addEventListener('drop', function (event) {

            const files = event.dataTransfer.files;

            if (!files || !files.length) {
                return;
            }

            /*
             * Use DataTransfer so the original
             * <input type="file" name="file"> remains
             * the actual form field sent to Flask.
             */

            try {

                const dataTransfer = new DataTransfer();

                dataTransfer.items.add(files[0]);

                uploadInput.files = dataTransfer.files;

                uploadInput.dispatchEvent(
                    new Event('change', { bubbles: true })
                );

            } catch (error) {

                console.warn(
                    'Drag-and-drop assignment is not supported by this browser.',
                    error
                );

            }

        });
    }


    /* =========================================================
       SCREENING FORM LOADING STATE
    ========================================================= */

    const screeningForm = document.querySelector(
        '[data-loading-form]'
    );

    if (screeningForm) {

        screeningForm.addEventListener('submit', function (event) {

            /*
             * Do not allow repeated submissions caused by
             * double-clicking the Analyze button.
             */

            if (screeningForm.classList.contains('loading')) {
                event.preventDefault();
                return;
            }

            screeningForm.classList.add('loading');

            const submitButton =
                document.getElementById('submit-button');

            if (submitButton) {
                submitButton.disabled = true;
            }

        });

    }


    /* =========================================================
       INPUT MICRO-INTERACTIONS
       Adds a visual class without changing form behaviour.
    ========================================================= */

    const formInputs = document.querySelectorAll(
        '.field-group input, .field-group select, .field-group textarea'
    );

    formInputs.forEach(function (input) {

        input.addEventListener('focus', function () {
            const parent = input.closest('.field-group');

            if (parent) {
                parent.classList.add('focused');
            }
        });

        input.addEventListener('blur', function () {
            const parent = input.closest('.field-group');

            if (parent) {
                parent.classList.remove('focused');
            }
        });

    });


    /* =========================================================
       IMAGE ERROR HANDLING
    ========================================================= */

    document.querySelectorAll('img').forEach(function (image) {

        image.addEventListener('error', function () {

            image.classList.add('image-load-error');

        });

    });


    /* =========================================================
       KEYBOARD ACCESSIBILITY
    ========================================================= */

    document.addEventListener('keydown', function (event) {

        if (event.key === 'Escape') {

            if (
                navigation &&
                navigation.classList.contains('open')
            ) {

                navigation.classList.remove('open');

                if (navButton) {
                    navButton.setAttribute(
                        'aria-expanded',
                        'false'
                    );

                    navButton.setAttribute(
                        'aria-label',
                        'Open navigation'
                    );
                }
            }

        }

    });

});