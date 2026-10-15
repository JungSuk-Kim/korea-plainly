/* Korea Plainly trip cost calculator: rough per-person costs in won, using the ranges in our budget guide. */
(function () {
  "use strict";
  var root = document.getElementById("kp-budget"); if (!root) return;
  // won per person per day: [stay, food, transport + sights]
  var STYLE = { backpacker: [35000, 30000, 20000], mid: [90000, 60000, 40000], comfort: [200000, 100000, 70000] };
  var KTX = 60000;      // a long KTX trip one way, e.g. Seoul to Busan, standard seat (approximate)
  var JEJU = 120000;    // a return domestic flight to Jeju (varies a lot by date)
  var AIRPORT = 20000;  // airport train or bus, both ways
  function f(id) { return root.querySelector("#" + id); }
  function won(n) { return (Math.round(n / 1000) * 1000).toLocaleString("en-GB") + " won"; }
  function calc() {
    var days = Math.max(1, Math.min(60, parseInt(f("bg-days").value, 10) || 1));
    var people = Math.max(1, Math.min(10, parseInt(f("bg-people").value, 10) || 1));
    var s = STYLE[f("bg-style").value];
    var share = people > 1 ? 0.7 : 1;   // sharing a room makes stays cheaper per person
    var stay = s[0] * share * (days - 1 > 0 ? days - 1 : 1), food = s[1] * days, local = s[2] * days;
    var trains = (parseInt(f("bg-ktx").value, 10) || 0) * KTX, jeju = f("bg-jeju").checked ? JEJU : 0;
    var shop = parseInt(f("bg-shop").value, 10) || 0;
    var each = stay + food + local + trains + jeju + AIRPORT + shop;
    var rows = [["Places to stay (" + Math.max(1, days - 1) + " nights" + (people > 1 ? ", sharing" : "") + ")", stay],
      ["Food and drink", food], ["Local transport and sights", local], ["Airport transfers", AIRPORT]];
    if (trains) rows.push(["KTX trips", trains]);
    if (jeju) rows.push(["Flight to Jeju and back", jeju]);
    if (shop) rows.push(["Shopping and extras", shop]);
    var out = f("bg-out"), html = "<table>";
    rows.forEach(function (r) { html += "<tr><td>" + r[0] + "</td><td>" + won(r[1]) + "</td></tr>"; });
    html += "<tr class='tot'><td>Per person</td><td>" + won(each) + "</td></tr>";
    if (people > 1) html += "<tr class='tot'><td>For " + people + " people</td><td>" + won(each * people) + "</td></tr>";
    html += "</table>";
    var rate = parseFloat(f("bg-rate").value), unit = f("bg-unit").value.trim() || "in your currency";
    if (rate > 0) html += "<p class='bg-conv'>About <b>" + Math.round(each / rate).toLocaleString("en-GB") + " " + unit + "</b> per person, at " + rate.toLocaleString("en-GB") + " won to 1 " + unit + ".</p>";
    html += "<p class='bg-day'>That is about " + won(each / days) + " per person per day, not counting international flights.</p>";
    out.innerHTML = html;
  }
  Array.prototype.forEach.call(root.querySelectorAll("input,select"), function (i) { i.addEventListener("input", calc); i.addEventListener("change", calc); });
  calc();
})();
