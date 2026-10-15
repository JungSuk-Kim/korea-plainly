/* Korea Plainly: which Korean city suits you? Five questions, points per city, one result with a link. */
(function () {
  "use strict";
  var root = document.getElementById("kp-cityquiz"); if (!root) return;
  var CITIES = {
    seoul: { name: "Seoul", link: "seoul.html", plan: "seoul-3-day-itinerary.html", text: "Palaces in the morning, markets at lunch, neon at night. Seoul has the most of everything, and it is where almost every first trip starts." },
    busan: { name: "Busan", link: "busan.html", plan: "busan-1-day-itinerary.html", text: "Beaches, seafood, a temple on the rocks and hillside villages. Korea's second city is big and lively, but it moves at a sea-side pace." },
    jeju: { name: "Jeju", link: "jeju.html", plan: "jeju-3-day-itinerary.html", text: "Volcano craters, black-rock beaches and green tea fields. Rent a car, slow down and follow the coast road." },
    gyeongju: { name: "Gyeongju", link: "gyeongju.html", plan: "gyeongju-1-day-itinerary.html", text: "A thousand-year-old royal capital with grassy tombs, temples and ponds lit up at night. Korea's open-air museum." },
    jeonju: { name: "Jeonju", link: "jeonju.html", plan: "jeonju.html", text: "Hundreds of tiled-roof hanok houses and the best bibimbap in the country. Stay a night in a traditional guesthouse." },
    gangneung: { name: "Gangneung", link: "gangneung.html", plan: "gangneung.html", text: "Beaches, lakes and Korea's favourite coffee street, two hours from Seoul by fast train. Easy, relaxed and by the sea." }
  };
  var Q = [
    ["What does your perfect day look like?", [["Exploring busy streets and shops", { seoul: 3, busan: 1 }], ["Walking by the sea", { busan: 3, gangneung: 2, jeju: 1 }], ["Hiking and big views", { jeju: 3, gangneung: 1 }], ["Old temples and history", { gyeongju: 3, jeonju: 2 }]]],
    ["Pick a meal.", [["Korean barbecue and late-night chicken", { seoul: 3 }], ["Fresh seafood by the harbour", { busan: 3, jeju: 1, gangneung: 1 }], ["A perfect bowl of bibimbap", { jeonju: 3 }], ["Coffee and pastries with a view", { gangneung: 3, jeju: 1 }]]],
    ["How do you like to get around?", [["Subway, everywhere", { seoul: 2, busan: 2 }], ["A rental car and the open road", { jeju: 3 }], ["On foot, slowly", { jeonju: 2, gyeongju: 2 }], ["A fast train out of the city", { gangneung: 2, gyeongju: 1, busan: 1 }]]],
    ["Evenings are for…", [["Night markets and city lights", { seoul: 3, busan: 1 }], ["Sunset on a beach", { busan: 2, jeju: 2, gangneung: 1 }], ["A lit-up palace pond", { gyeongju: 3 }], ["Tea in a quiet hanok", { jeonju: 3 }]]],
    ["How much time do you have?", [["A few days", { seoul: 2, gangneung: 1 }], ["About a week", { busan: 2, gyeongju: 1 }], ["Ten days or more", { jeju: 2, jeonju: 1 }], ["I'm already in Seoul and want a trip out", { gangneung: 2, jeonju: 2, gyeongju: 1 }]]]
  ];
  var step = 0, score = {};
  var box = root.querySelector(".cq-box");
  function show() {
    box.innerHTML = "";
    if (step < Q.length) {
      var p = document.createElement("p"); p.className = "cq-step"; p.textContent = "Question " + (step + 1) + " of " + Q.length; box.appendChild(p);
      var h = document.createElement("h3"); h.textContent = Q[step][0]; box.appendChild(h);
      Q[step][1].forEach(function (a) {
        var b = document.createElement("button"); b.type = "button"; b.className = "cq-a"; b.textContent = a[0];
        b.addEventListener("click", function () { Object.keys(a[1]).forEach(function (c) { score[c] = (score[c] || 0) + a[1][c]; }); step++; show(); });
        box.appendChild(b);
      });
      return;
    }
    var best = Object.keys(CITIES).sort(function (a, b) { return (score[b] || 0) - (score[a] || 0); });
    var c = CITIES[best[0]], second = CITIES[best[1]];
    box.innerHTML = "<div class='cq-res'><img src='kkachi.png' alt='Kkachi the magpie' width='90' height='97'><div>" +
      "<p class='cq-step'>Kkachi thinks you'll love</p><h3>" + c.name + "</h3><p>" + c.text + "</p>" +
      "<p><a class='cq-go' href='" + c.link + "'>Read our " + c.name + " guide →</a></p>" +
      "<p class='cq-more'>Runner-up: <a href='" + second.link + "'>" + second.name + "</a>. Planning the whole trip? See our <a href='korea-7-day-itinerary.html'>7 days in Korea</a> plan.</p>" +
      "<p><button type='button' class='cq-share'>Share my result</button> <button type='button' class='cq-again'>Try again</button></p></div></div>";
    box.querySelector(".cq-again").addEventListener("click", function () { step = 0; score = {}; show(); });
    box.querySelector(".cq-share").addEventListener("click", function () {
      var text = "Kkachi says my Korean city is " + c.name + "! Which one is yours?", url = location.href.split("#")[0];
      if (navigator.share) { navigator.share({ title: "Which Korean city suits you?", text: text, url: url }).catch(function () {}); return; }
      try { navigator.clipboard.writeText(text + " " + url); this.textContent = "Link copied!"; } catch (e) { this.textContent = url; }
    });
  }
  show();
})();
