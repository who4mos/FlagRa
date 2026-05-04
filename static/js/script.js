const toggler = document.querySelector("#theme-toggle");
const html = document.documentElement;

toggler.addEventListener("click", () => {
    const currTheme = html.getAttribute("data-bs-theme");
    const newTheme = currTheme == "light" ? "dark" : "light";

    localStorage.setItem("theme", newTheme);
    html.setAttribute("data-bs-theme", newTheme);
});
