// Update data to an existing chart
function parseData(courseResults) {
  // Loop through each course and return a well-formatted data point
  // for the chart.
  // The map loops over each assignment and finds the average score, packing
  // it against a specific assignment.
  return courseResults.map((course) => {
    return {
      label: course.name,
      data: course.assignments.map((assignment) => assignment.avg),
    };
  });
}

htmx.on("buildChart", (response) => {
  let results = response.detail.value;
  ctx = document.querySelector(`#chart`).getContext(`2d`);

  // Get rid of any existing charts on the page. It's easier to rebuild
  // a new chart object than keeping track of old and new data with
  // different structures.
  if (chart instanceof Chart) {
    chart.destroy();
  }

  console.log(results);
  if (!results[0].assignments) {
    showToast("No data for this standard.");
    return;
  }

  data = {
    labels: results[0].assignments.map((item) => item.assignment),
    datasets: parseData(results),
  };

  chart = new Chart(ctx, {
    type: "line",
    data: data,
    options: {
      plugins: {
        legend: {
          position: "right",
        },
      },
      scales: {
        y: {
          min: 0,
          max: 2,
          afterTickToLabelConversion: function (chart) {
            (chart.ticks = []),
              chart.ticks.push({ value: 0, label: "Did not demonstrate" }),
              chart.ticks.push({ value: 1, label: "Revision needed" }),
              chart.ticks.push({ value: 2, label: "Met expectations" });
          },
        },
        x: {
          title: {
            display: true,
            text: "Assignment",
          },
        },
      },
      tension: 0.1,
    },
  });
});
