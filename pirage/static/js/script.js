// Update these
var postUrl = "/click";
var listenUrl = "/stream";
var lockUrl = "/set_lock";
var pirUrl = "/set_pir";
var dweetUrl = "/set_dweet"

jQuery["postJSON"] = function( url, data, callback ) {
    // shift arguments if data argument was omitted
    if ( jQuery.isFunction( data ) ) {
        callback = data;
        data = undefined;
    }

    return jQuery.ajax({
        url: url,
        type: "POST",
        contentType:"application/json",
        dataType: "json",
        data: JSON.stringify(data),
        success: callback
    });
};

// Idk what the service will send back, but could look like this - delete when done
var fakeTestData = {
    mag: true,
    pir: false,
    temp: 63.5,
    locked: false,
    pir_enabled: true,
    dweet_enabled: true,
    times: {
      now: 0,
      last_mag: "None",
      last_pir: "None"
    }
}

$(document).ready(function () {

    updatePage(fakeTestData); // Loading test, remove me when done

    $("#button").on("click", toggleDoor);

    $("#lock").on("click", toggleLock);

    $("#pir").on("click", togglePir);

    $("#dweet").on("click", toggleDweet);
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

function toggleLock() {
  var locked = $('#lock').attr('data-locked') === 'true';
  $.postJSON(lockUrl, { locked: !locked },
    function(data) {
      console.log(data);
      $("#lock").attr("data-locked", data.locked);
    });
}

function togglePir() {
  var enabled = $('#pir').attr('data-pir-enabled') === 'true';
  $.postJSON(pirUrl, { enabled: !enabled },
    function(data) {
      console.log(data);
      $("#pir").attr("data-pir-enabled", data.pir_enabled);
    });
}

function toggleDweet() {
  var enabled = $('#dweet').attr('data-dweet-enabled') === 'true';
  $.postJSON(dweetUrl, { enabled: !enabled },
    function(data) {
      console.log(data);
      $("#dweet").attr("data-dweet-enabled", data.dweet_enabled);
    });
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
    $("#lock").attr("data-locked", data.locked);
    $("#pir").attr("data-pir-enabled", data.pir_enabled);
    $("#dweet").attr("data-dweet-enabled", data.dweet_enabled);
    // console.log($("#pir").data("pir-enabled"));
}
