const toggler = document.querySelector("#theme-toggle");
const html = document.documentElement;

function updateTogglerText(theme) {
    if (theme === "dark") {
        toggler.innerHTML = "<i class='bi bi-sun-fill'></i> Light Mode";

    } else {
        toggler.innerHTML = "<i class='bi bi-moon'></i> Dark Mode";
    }
}

const initialTheme = html.getAttribute("data-bs-theme");
updateTogglerText(initialTheme);

toggler.addEventListener("click", () => {
    const currTheme = html.getAttribute("data-bs-theme");
    const newTheme = currTheme == "light" ? "dark" : "light";

    localStorage.setItem("theme", newTheme);
    html.setAttribute("data-bs-theme", newTheme);

    updateTogglerText(newTheme);
});
