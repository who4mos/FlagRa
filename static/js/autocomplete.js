const dataElement = document.getElementById("candidates-data");
const candidateList = JSON.parse(dataElement.textContent);

const inputElement = document.getElementById("country-input");
const listElement = document.getElementById("autocomplete-list");

let currentFocus = 0;
  
inputElement.addEventListener("input", (e) => {
    const text = e.target.value.toLowerCase();

    if (!text) {
        listElement.style.display = "none";
        return;
    }
      
    listElement.innerHTML = "";
    const matches = candidateList.filter(
        country => country.toLowerCase().startsWith(text)
            && country.toLowerCase() !== text
    );

    if (matches.length > 0) {
        listElement.style.display = "block";
          
        for (let match of matches) {
            const li = document.createElement("li");
            li.classList.add('list-group-item');
            li.textContent = match;

            li.addEventListener("click", () => {
                inputElement.value = match;
                listElement.style.display = "none";
            })
              
            listElement.appendChild(li);
        }

        currentFocus = 0; 
        const items = listElement.getElementsByTagName("li");
        setActive(items);
    } else {
        listElement.style.display = "none";
    }
});

inputElement.addEventListener("keydown", (e) => {
    if (listElement.style.display === "none") return;

    const items = listElement.getElementsByTagName("li");

    if (e.key === "ArrowDown") {
        if (currentFocus + 1 === items.length) {
            currentFocus = 0;
        } else {
            currentFocus++;
        }

        setActive(items);
    } else if (e.key === "ArrowUp") {
        if (currentFocus - 1 < 0) {
            currentFocus = items.length - 1;
        } else {
            currentFocus--;
        }

        setActive(items);
    } else if (e.key === "Enter" || e.key === "Tab") {
        if (e.key === "Enter") {
            e.preventDefault();
        }
          
        items[currentFocus].click();
    }
      
});

function setActive(items) {
    if (!items || items.length === 0) return;

    for (let i = 0; i < items.length; i++) {
        items[i].classList.remove("active");
    }

    items[currentFocus].classList.add("active");
}
