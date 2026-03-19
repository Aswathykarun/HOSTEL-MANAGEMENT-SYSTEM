function addStudent() {
    alert("Redirect to Add Student Form");
}

function postNotice() {
    let msg = prompt("Enter Notice:");

    fetch("/add_notice", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: msg })
    });

    alert("Notice Posted!");
}