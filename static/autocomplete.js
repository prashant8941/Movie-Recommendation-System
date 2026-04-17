new autoComplete({
    data: {
        src: films, // This variable must be defined in your home.html script tag
        cache: true,
    },
    selector: "#autoComplete",
    threshold: 2,
    debounce: 100,
    searchEngine: "loose", // "loose" is better for matching partial titles
    resultsList: {
        render: true,
        container: source => {
            source.setAttribute("id", "autoComplete_list"); // FIXED: Matches the ID used in noResults
        },
        destination: document.querySelector("#autoComplete"),
        position: "afterend",
        element: "ul"
    },
    maxResults: 5,
    highlight: true,
    resultItem: {
        content: (data, source) => {
            source.innerHTML = data.match;
        },
        element: "li"
    },
    noResults: () => {
        const result = document.createElement("li");
        result.setAttribute("class", "no_result");
        result.setAttribute("tabindex", "1");
        result.setAttribute("style", "list-style: none; color: red; text-align: center;");
        result.innerHTML = "No Results Found";
        
        // Safely check if the list exists before appending
        const list = document.querySelector("#autoComplete_list");
        if (list) {
            list.appendChild(result);
        }
    },
    onSelection: feedback => {
        // Set the value and trigger the button enablement logic
        const inputField = document.getElementById('autoComplete');
        inputField.value = feedback.selection.value;
        
        // Force the search button to enable once a selection is made
        $('.movie-button').prop('disabled', false);
    }
});