// Format a date for display
function formatDate(target, strDate) {
  let date = new Date(strDate);

  const formats = {
    dateOnly: {
      year: "numeric",
      month: "numeric",
      day: "numeric",
    },
  };

  return new Intl.DateTimeFormat("en", formats[target]).format(date);
}

function showToast(msg, err = false) {
  console.log("Toasted!");
  const toast = document.querySelector(`#toast`);
  // Handle message objects from hyperscript
  // For non-template returns, the backend will also return JSON with
  // the `message` key with details for the user.
  if (typeof msg === "object") {
    // HTMX returns strings, so convert it to an object
    msg = msg.value;
  }

  toast.children[0].innerText = msg;
  if (err) {
    toast.classList.add("error");
  }
  toast.classList.add("show");
  setTimeout(() => {
    toast.classList.remove("show");
    if (err) {
      toast.classList.remove("error");
    }
  }, 5000);
}

function cancelToast() {
  const toast = document.querySelector(`#toast`);
  toast.classList.remove("show");
  clearTimeout();
}

// Listen for toast messaging from the server
htmx.on("showToast", (event) => {
  showToast(event.detail);
});

// TODO: Doesn't run after hard refresh?
function checkActivePage() {
  let path = window.location.pathname;
  if (path.split("/").length > 2) {
    let id = path.split("/")[2];

    let el = document.querySelector(`#course-${id}`);
    if (el) {
      el.classList.add("active");
    }
  }
  return;
}

function bulkAddInfo(formData) {
  let elements = {
    assignment: document.querySelectorAll("input[name='assignment']"),
    score: document.querySelectorAll("input[name='score']"),
    comments: document.querySelectorAll("textarea"),
  };

  for (let key in formData) {
    setBulkValue(elements[key], formData[key]);
  }
}

function setBulkValue(els, val) {
  els.forEach((el) => (el.value = val));
}

// Handle errors from the server
document.addEventListener("htmx:responseError", (evt) => {
  showToast(evt.detail.xhr.responseText, true);
});

// document.addEventListener('htmx:beforeSend', (evt) => {
//     showToast('Loading...')
// })

// For debugging requests
// document.addEventListener('htmx:beforeSend', function(evt) {
//     console.info('Dispatched...')
//     console.info(evt.detail)
// })

// Hyperscript can only access global function names. Because this
// is in a module, it has to be assigned explicitely to the
// Window object.
window.formatDate = formatDate;
window.toast = showToast;
window.cancelToast = cancelToast;
window.checkActivePage = checkActivePage;
window.bulkAddInfo = bulkAddInfo;
