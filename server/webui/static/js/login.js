  document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('loginForm');
    const loginBtn = document.getElementById('loginBtn');
    const passwordInput = document.getElementById('password');

    // Add loading state on form submit
    loginForm.addEventListener('submit', function (e) {
      loginBtn.classList.add('loading');
      loginBtn.disabled = true;

      // Remove loading state after 3 seconds if still on page
      setTimeout(() => {
        loginBtn.classList.remove('loading');
        loginBtn.disabled = false;
      }, 3000);
    });

    // Add enter key support
    passwordInput.addEventListener('keypress', function (e) {
      if (e.key === 'Enter') {
        loginForm.submit();
      }
    });

    // Focus password input on page load
    passwordInput.focus();

    // Add typing effect to placeholder
    const originalPlaceholder = passwordInput.placeholder;
    let placeholderIndex = 0;
    let isDeleting = false;

    function typePlaceholder() {
      if (!document.activeElement === passwordInput && passwordInput.value === '') {
        if (!isDeleting && placeholderIndex < originalPlaceholder.length) {
          passwordInput.placeholder = originalPlaceholder.substring(0, placeholderIndex + 1);
          placeholderIndex++;
        } else if (isDeleting && placeholderIndex > 0) {
          passwordInput.placeholder = originalPlaceholder.substring(0, placeholderIndex - 1);
          placeholderIndex--;
        } else {
          isDeleting = !isDeleting;
        }
      }
    }

    // Start placeholder animation
    setInterval(typePlaceholder, 100);
  });
