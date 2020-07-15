// Journal/Genus hide/show appropriate input
// Compound hide-show NPAID replace form
$(() => {
  showJournal();
  showGenus();
  showNPAID();
  $("#journalSelect").change(() => {
    showJournal();
  });
  $("#genusSelect").change(() => {
    showGenus();
  });
  $("#compoundSelect").change(() => {
    showNPAID();
  });
});

// Journal auto-complete
$(() => {
  $(".altJournal").autocomplete({
    source: (request, response) => {
      $.getJSON(
        "/_search_journal",
        {
          search: request.term,
        },
        (data) => {
          response(data.results);
        }
      );
    },
    minLength: 2,
  });
});

// Genus auto-complete
$(() => {
  $("#alt_taxon_name").autocomplete({
    source: (request, response) => {
      $.getJSON(
        "/_search_taxon",
        {
          search: request.term,
          rank: $("#taxon_rank").children("option:selected").val(),
        },
        (data) => {
          response(data.results);
        }
      );
    },
    minLength: 2,
  });
});

function showNPAID() {
  selected = $("#compoundSelect").children("option:selected").val();
  if (selected === "replace") {
    $("#npaid").show();
  } else {
    $("#npaid").hide();
  }
}

function showJournal() {
  selected = $("#journalSelect").children("option:selected").val();
  if (selected === "alt") {
    $(".newJournal").hide();
    $(".altJournal").show();
  } else if (selected === "new") {
    $(".newJournal").show();
    $(".altJournal").hide();
  }
}

function showGenus() {
  selected = $("#genusSelect").children("option:selected").val();
  if (selected === "alt") {
    $(".newTaxon").hide();
    $(".altGenus").show();
  } else if (selected === "new") {
    $(".newTaxon").show();
    $(".altGenus").hide();
  }
}
