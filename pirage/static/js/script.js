// Update these
var postUrl = "/click";
var listenUrl = "/stream";

// Idk what the service will send back, but could look like this - delete when done
var fakeTestData = {
    mag: true,
    pir: false,
    temp: 63.5,
    times: {
      now: 0,
      last_mag: "None",
      last_pir: "None"
    }
}

$(document).ready(function () {

    updatePage(fakeTestData); // Loading test, remove me when done

    $("#button").on("click", toggleDoor);
});

// No idea if this works, nor how to test it
// http://flask.pocoo.org/snippets/116/
var eventSource = new EventSource(listenUrl);
eventSource.onmessage = function (e) {
    updatePage(JSON.parse(e.data));
    $("#log").html(e.data);
};

// Sends request to server to open/close door (presumes that server knows the door's state)
function toggleDoor() {
    $.post(postUrl,"").done(function(x) {
        alert("done!");
    }).fail(handleFail);
}

function handleFail() {
    // Finish me - this fires on 400/500 errors
    // Shouldn't need to handle success since the listener will update the UI once the server pushes a message
    alert("TODO: Implement failure handling");
}

function updatePage(data) {
    $("[data-door-open]").attr("data-door-open", data.mag);
    $("#last-mag").html(data.times.last_mag);
    $("#last-pir").html(data.times.last_pir);
}