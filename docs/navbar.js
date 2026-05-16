/**
 * Global navbar — injected into every page.
 * Detects readme.html to show the search button and adjust hrefs.
 */
(function () {
  const isReadme = /readme\.html/i.test(location.pathname);
  const base = isReadme ? "index.html" : "";

  const navLinks = [
    { label: "Tutorials",  href: base + "#tutorials" },
    { label: "Workflow",   href: base + "#workflow"  },
    { label: "Reference",  href: base + "#reference" },
    { label: "Commands",   href: base + "#commands"  },
    { label: "Full Guide", href: "readme.html", current: isReadme },
  ];

  const linksHTML = navLinks
    .map(
      (l) =>
        `<a href="${l.href}"${l.current ? ' aria-current="page"' : ""}>${l.label}</a>`
    )
    .join("");

  const searchBtnHTML = isReadme
    ? `<button class="topbar-search-btn" id="search-trigger" aria-label="Search the full guide (⌘K)">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <span class="search-btn-label">Search</span>
      </button>`
    : "";

  const nav = document.createElement("nav");
  nav.className = "topbar";
  nav.setAttribute("aria-label", "Site navigation");
  nav.innerHTML = `
    <a class="brand" href="${isReadme ? "index.html" : "#top"}">ApplyForge Docs</a>
    <div class="topbar-links">${linksHTML}</div>
    ${searchBtnHTML}
    <button class="topbar-menu-btn" id="menu-toggle" aria-label="Toggle navigation" aria-expanded="false">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2.5" stroke-linecap="round" aria-hidden="true">
        <line x1="3" y1="6" x2="21" y2="6"/>
        <line x1="3" y1="12" x2="21" y2="12"/>
        <line x1="3" y1="18" x2="21" y2="18"/>
      </svg>
    </button>
  `;

  const header = document.querySelector("header");
  if (header) header.prepend(nav);

  // Hamburger toggle
  const menuBtn = nav.querySelector("#menu-toggle");
  menuBtn.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    menuBtn.setAttribute("aria-expanded", String(open));
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".topbar")) {
      nav.classList.remove("open");
      menuBtn.setAttribute("aria-expanded", "false");
    }
  });

  nav.querySelectorAll(".topbar-links a").forEach((a) => {
    a.addEventListener("click", () => {
      nav.classList.remove("open");
      menuBtn.setAttribute("aria-expanded", "false");
    });
  });
}());
