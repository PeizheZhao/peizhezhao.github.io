(function () {
  var nav = document.querySelector("[data-responsive-nav]");

  if (!nav) {
    return;
  }

  var links = nav.querySelector("[data-nav-links]");
  var toggle = nav.querySelector("[data-nav-toggle]");
  var menu = nav.querySelector("[data-nav-menu]");
  var masthead = nav.closest ? nav.closest(".masthead") : null;
  var frame = null;
  var buffer = 1;

  if (!links || !toggle || !menu) {
    return;
  }

  function closeMenu() {
    nav.classList.remove("is-open");
    if (masthead) {
      masthead.classList.remove("masthead--nav-open");
    }
    toggle.classList.remove("close");
    toggle.setAttribute("aria-expanded", "false");
    menu.hidden = true;
  }

  function measureLinksWidth() {
    var previousPosition = links.style.position;
    var previousVisibility = links.style.visibility;
    var previousWidth = links.style.width;
    var previousMaxWidth = links.style.maxWidth;

    links.style.position = "absolute";
    links.style.visibility = "hidden";
    links.style.width = "max-content";
    links.style.maxWidth = "none";

    var width = links.scrollWidth;

    links.style.position = previousPosition;
    links.style.visibility = previousVisibility;
    links.style.width = previousWidth;
    links.style.maxWidth = previousMaxWidth;

    return width;
  }

  function updateNavMode() {
    frame = null;

    var shouldCollapse = measureLinksWidth() > nav.clientWidth - buffer;

    nav.classList.toggle("is-collapsed", shouldCollapse);
    nav.classList.add("is-ready");
    if (masthead) {
      masthead.classList.toggle("masthead--nav-collapsed", shouldCollapse);
    }

    if (!shouldCollapse) {
      closeMenu();
    }
  }

  function scheduleUpdate() {
    if (frame) {
      return;
    }

    frame = window.requestAnimationFrame(updateNavMode);
  }

  toggle.addEventListener("click", function () {
    var isOpen = !nav.classList.contains("is-open");

    nav.classList.toggle("is-open", isOpen);
    if (masthead) {
      masthead.classList.toggle("masthead--nav-open", isOpen);
    }
    toggle.classList.toggle("close", isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
    menu.hidden = !isOpen;
  });

  menu.addEventListener("click", function (event) {
    if (event.target.closest("a")) {
      closeMenu();
    }
  });

  document.addEventListener("click", function (event) {
    if (!nav.contains(event.target)) {
      closeMenu();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeMenu();
    }
  });

  if ("ResizeObserver" in window) {
    var observer = new ResizeObserver(scheduleUpdate);
    observer.observe(nav);
    observer.observe(links);
  } else {
    window.addEventListener("resize", scheduleUpdate);
  }

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(scheduleUpdate);
  }

  window.addEventListener("load", scheduleUpdate);
  scheduleUpdate();
})();
