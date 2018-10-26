$(document).ready(() => {

    // For page to reload when the back button was used
    window.addEventListener( "pageshow", function ( event ) {
        var historyTraversal = event.persisted ||
                               ( typeof window.performance != "undefined" &&
                                    window.performance.navigation.type === 2 );
        if ( historyTraversal ) {
          // Handle page restore.
          window.location.reload(true);
        }
      });

    // variables
    const regex = /^10.\d{4,9}\//g;

    // Catch new compound alert
    newCompound = false
    $(".alert").each(function(idx) {
        if ($(this).text().includes("Error in the Compounds field - {'name': ['This field is required.'], 'smiles': ['This field is required.'], 'source_organism': ['This field is required.']}")) {
            newCompound = true;
        } else {
            $(this).show();
        }

    })

    // Initialize SmilesDrawer
    var options = {
        width: 400,
        height: 400
    }
    var smilesDrawer = new SmilesDrawer.Drawer(options);

    // Draw compounds on page load
    $(".smiles-input").each( function(idx) {
        let $this = $(this);
        let smiles = $this.val().trim()
        console.log(idx + " " + smiles);
        let $canvas = $("#compound-canvas-"+idx)
        $canvas.attr("alt", smiles);
        // $canvas.next().html()
        // Parse and draw compound
        SmilesDrawer.parse(smiles, function(tree) {
            // console.log(tree);
            smilesDrawer.draw(tree, "compound-canvas-" + idx, "light", false);
            $canvas.next().text(smilesDrawer.getMolecularFormula());
        }, function(err) {
            console.log(err);
        });
    });

    // Add tab buttons and menu items for each compound
    $(".compound-row").each( function() {
        let $this = $(this);
        let rowNum = parseInt($this.attr("id").split("-")[2]);
        let compoundName = $this.find("#compounds-"+rowNum+"-name").val();
        let compoundKnown = $this.find("#compounds-"+rowNum+"-curated_compound").is(":checked");
        if (compoundName.length == 0) {
            compoundName = "Name";
        }
        var btnType;
        if (compoundKnown){
            btnType = 'btn-success';
        } else {
            btnType = 'btn-warning';
        }

        // Buttons
        let btnString = "<button class='compound-tab btn "+btnType+"' id='compound-tab-"+rowNum+"' type=button>";
        btnString = btnString + compoundName + "</button>";
        $("#tabDiv").append(btnString);

        // Menu Items
        let menuItemString = "<li role='presentation'><button class='compound-menu' role='menuitem' id='compound-menu-"+rowNum+"' type=button>";
        menuItemString = menuItemString + compoundName + "</a></li>";
        $("#compoundMenu").append(menuItemString);
    })

    // Show correct # of compounds on menu
    updateMenuCount()

    // Hide all but first for compound field unless just added new compound
    // If new compound (catching by error), show that one
    $(".compound-row").hide();
    if ( newCompound ){
        $(".compound-row").last().show();
        $(".compound-tab").last().addClass("active");
        $tabDiv = $("#tabDiv")
        $tabDiv.scrollLeft($tabDiv.width()*20)
    } else {
        $(".compound-row").first().show();
        $(".compound-tab").first().addClass("active");
    }

    // Smiles input event
    $(".smiles-input").on("keyup", function() {
        let $this = $(this);
        let smiles = $this.val().trim();
        // console.log(smiles);
        let rowNum = parseInt($this.attr("id").split("-")[1]);
        let $canvas = $("#compound-canvas-"+rowNum)
        $canvas.attr("alt", smiles);
        // console.log(smiles.length);
        if (smiles.length == 0 ){
            $canvas[0].getContext("2d").clearRect(0, 0, $canvas[0].width, $canvas[0].height);
            $canvas.next().text(" ")
        } else {
        // Parse and draw compound
        SmilesDrawer.parse(smiles, function(tree) {
            // console.log(tree);
            smilesDrawer.draw(tree, "compound-canvas-" + rowNum, "light", false);
            $canvas.next().text(smilesDrawer.getMolecularFormula());
        }, function(err) {
            console.log(err);
        });
        }
    });

    // HACKY SOLUTION - USED PYTHON and AJAX TO ADD COMPOUND
    // This actually works very well
    // Add row event
    // $("#add-compound").on("click", function() {
    //     let $this = $("#compound-fieldset");
    //     // console.log($this);
    //     let oldRow = $this.find(".compound-row:last");
    //     var row = oldRow.clone(true, true);
    //     let rowNum = parseInt(row[0].id.split("-")[2]) + 1;
    //     // console.log(rowNum);
    //     row.attr("id", "compound-row-"+ rowNum);
    //     row.find("input").each( function() {
    //         let $input = $(this);
    //         let id = $input.attr("id");
    //         let newId = id.replace( /\d{1,4}/g, rowNum.toString());
    //         $input.attr("id", newId).attr("name", newId).attr("value", "").val("");
    //         $input.prev().attr("for", newId);
    //         // console.log($input);
    //     });
    //     row.find("canvas").each( function() {
    //         $(this).attr("id", "compound-canvas-"+rowNum).removeAttr("alt");
    //     });
    //     row.find("h4").each( function() {
    //         $(this).text("");
    //         $(this).attr("id", "compound-formula-"+rowNum)
    //     });

    //     // Hide previous row and show new one
    //     oldRow.after(row);
    //     $(".compound-row").hide();
    //     row.show();

    //     // Create new button and add
    //     let lastBtn = $(".compound-tab").last();
    //     let btn = lastBtn.clone(true, true);
    //     btn.text("New Compound").attr("id", "compound-tab-"+rowNum);

    //     // Make tab appear active
    //     $(".compound-tab").removeClass("active");
    //     btn.addClass("active");
    //     lastBtn.after(btn);
    //     $("#tabDiv").scrollLeft(btn.offset().left);
    // });

    // Compound select from tabs
    $(".compound-tab").on("click", function() {
        let rowNum = $(this).attr("id").split("-")[2];
        let $target = $("#compound-row-"+rowNum);
        // Hide all compound rows first then show target
        $(".compound-row").hide();
        $target.show();
        // Scroll tab to center
        scrolltabDiv(rowNum)
        // Make tab appear active
        $(".compound-tab").removeClass("active");
        $(this).addClass("active");
    });

    // Compound select from menu
    $(".compound-menu").on("click", function(e) {
        e.preventDefault()
        let rowNum = $(this).attr("id").split("-")[2];
        let $this = $("#compound-tab-"+rowNum);
        let $target = $("#compound-row-"+rowNum);
        // Hide all compound rows first then show target
        $(".compound-row").hide();
        $target.show();
        // Scroll tab to center
        scrolltabDiv(rowNum)
        // Make tab appear active
        $(".compound-tab").removeClass("active");
        $this.addClass("active");
    })

    // Write Name to Tab after leave input
    $(".name-input").on("blur", function() {
        let rowNum = $(this).attr("id").split("-")[1];
        let $target1 = $("#compound-tab-"+rowNum);
        let $target2 = $("#compound-menu-"+rowNum);
        // console.log($(this).val());
        if ($(this).val().length > 0) {
            $target1.text($(this).val());
            $target2.text($(this).val());
        } else {
            $target1.text("Name");
            $target2.text("Name");
        }
    });

    // Compound Curated Toggle
    $(".known-compound-input").on("change", function() {
        let rowNum = $(this).attr("id").split("-")[1];
        let $target = $("#compound-tab-"+rowNum);
        if ($(this).is(":checked")) {
            $target.removeClass("btn-warning");
            $target.addClass("btn-success");
        } else {
            $target.removeClass("btn-success");
            $target.addClass("btn-warning");
        }
    });

    // Remove row event
    $("button[data-toggle=fieldset-remove-row]").on("click", function() {
        let $this = $("#compound-fieldset");
        // console.log($(this));
        if ($this.find(".compound-row").length > 1) {
            let thisRow = $(this).closest(".compound-row");
            // console.log(thisRow)
            let rowNum = thisRow.attr("id").split("-")[2];
            thisRow.remove();
            // Remove tab and menu-item too
            $("#compound-tab-"+rowNum).remove();
            $("#compound-menu-"+rowNum).remove();
            // Deactivate all tabs
            $(".compound-tab").removeClass("active");
            // Show last row
            if (parseInt(rowNum) == 0) {
                $(".compound-tab").first().addClass("active");
                $(".compound-row").first().show();
            } else {
                $("#compound-tab-"+(rowNum-1)).addClass("active");
                $("#compound-row-"+(rowNum-1)).show();
            }
        } else {
            console.log("Not enough rows to remove.")
        }
        updateMenuCount();
    });

    // DOI Linkout
    if ($("input[id='doi']").val().match(regex)) {
        let link = "https://doi.org/" + $("input[id='doi']").val();
        $("#doi-link").attr("href", link).show();
    }

    // DOI Linkout event
    $("input[id='doi']").on("keyup", function() {
        // console.log($(this));
        let doi = $(this).val();
        // console.log(doi);
        $target = $("#doi-link");
        if (doi.match(regex)) {
            let link = "https://doi.org/" + doi;
            $target.attr("href", link).show();
        } else {
            $target.attr("href", "#").hide();;
        }
    });

    // PMID Linkout
    if (parseInt($("input[id='pmid']").val())) {
        let link = "https://www.ncbi.nlm.nih.gov/pubmed/" + $("input[id='pmid']").val()
        $("#pmid-link").attr("href", link).show();
    }

    // PMID Linkout event
    $("input[id='pmid']").on("keyup", function() {
        // console.log($(this));
        let pmid = $(this).val();
        $target = $("#pmid-link");
        if (parseInt(pmid) > 0) {
            let link = "https://www.ncbi.nlm.nih.gov/pubmed/" + pmid;
            $target.attr("href", link).show();
        } else {
            $target.attr("href", "#").hide();
        }
    });

    // Forward an article
    $("#fwdArticle").on("click", function() {
        let currentUrl = window.location.pathname;
        $.post('/data/nextArticle', {
            url: currentUrl
        }).done( function(retJson) {
            console.log(retJson['url']);
            if (retJson['url']) {
                window.location.replace(window.location.origin + '/' + retJson['url']);
            } else {
                alert("No next article.")
            }
        }).fail( function() {
            alert("Could not access server. Please contact the admin.")
        });
    });

    // Back an article
    $("#backArticle").on("click", function() {
        let currentUrl = window.location.pathname;
        $.post('/data/backArticle', {
            url: currentUrl
        }).done( function(retJson) {
            console.log(retJson['url']);
            if (retJson['url']) {
                window.location.replace(window.location.origin + '/' + retJson['url']);
            } else {
                alert("No previous article.")
            }
        }).fail( function() {
            alert("Could not access server. Please contact the admin.")
        });
    });

});

String.prototype.format = function () {
    var i = 0, args = arguments;
    return this.replace(/{}/g, function () {
      return typeof args[i] != 'undefined' ? args[i++] : '';
    });
  };

function updateMenuCount() {
    let $this = $("#compoundMenuBtn");
    let n = $(".compound-menu").length;
    $this.text("Curated Compounds ({})".format(n));
}

function scrolltabDiv(rowNum) {
        let $this = $("#compound-tab-"+rowNum)
        // Scroll tab to center
        // Only if not clicking active tab
        if (!($this.hasClass("active"))) {
            var out = $("#tabDiv");
            var tar = $this;
            var x = out.width();
            var y = tar.outerWidth(true);
            var z = tar.index();
            var q = 0;
            var m = out.find('button');
            //Just need to add up the width of all the elements before our target.
            for(var i = 0; i < z; i++){
                q+= $(m[i]).outerWidth(true);
            }
            out.scrollLeft(Math.max(0, q - (x - y)/2));
        }
}