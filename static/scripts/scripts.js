// Highlight current page in navbar
document.addEventListener('DOMContentLoaded', function() {
    
    /*
    var navs = document.getElementsByClassName('nav-link');
    var loc = location.href;
    for (var i = 0; i < navs.length; i++) {
        if (navs[i] == loc) {
            //Add active class to apply styling
            navs[i].classList.add('active');
        }
    }
    */

});

// Set all event listeners listeners
// Build page
if (window.location.pathname.indexOf('build') > -1) {
    document.addEventListener('DOMContentLoaded', function() {

        // 'Get sentences' click
        var form = document.getElementById('input'); // RENAME TO MAKE CLEARER
        form.addEventListener('submit', function(event){
            event.preventDefault();

            var formData = new FormData(form);
            
            // Set "loading" style
            document.getElementById('placeholder-text').innerHTML = 'Fetching sentences';
            document.getElementById('placeholder-text').removeAttribute('hidden');
            document.getElementById('progress').removeAttribute('hidden');
    
            // Get sentences from server (AJAX)
            dataRequest(formData);
        });

        // Sentence reload request
        var reload = document.getElementById('output');
        reload.addEventListener('submit', function(event){
            event.preventDefault();

            var reloadData = new FormData(reload);
            reloadRequest(reloadData);
        });
        
        // Add file name below icon
        const actualBtn = document.getElementById('actual-btn');
        const fileChosen = document.getElementById('file-text');

        actualBtn.addEventListener('change', function(){
            fileChosen.textContent = this.files[0].name
        }); 

        // Add tile click (MAKE BELOW A FUNCTION AND CALL HERE)
        var addTile = document.getElementById('add_tile');
        addTile.addEventListener('click', function(event) {
            event.preventDefault();
            
            // Count tile elements on page
            var container = document.getElementById('fields');
            var tileCount = container.children.length;
            
            // Prevent infinite tiles being added
            if (tileCount < 4) {
                // Get and copy first tile
                var tile = container.getElementsByTagName('div')[0];
                var newTile = tile.cloneNode(true);

                // Change new tiles title / inner select's name attribute
                newTile.getElementsByClassName('tile-title')[0].innerHTML = 'Extra';
                newTile.getElementsByTagName('select')[0].setAttribute('name', tileCount);
                
                // Add new tile to DOM
                container.appendChild(newTile);
            }            
        });

        // Remove tile (last first) (MAKE BELOW A FUNCTION AND CALL HERE)
        var removeTile = document.getElementById('remove_tile');
        removeTile.addEventListener('click', function(event) {
            event.preventDefault();

            var container = document.getElementById('fields');
            var lastTile = container.lastChild;
            
            // Keep two tiles
            if (container.children.length > 2) {
                lastTile.remove();
            }
        });
    });
}

// Add collapsible elements on About page
if (window.location.pathname == "/about") {
    document.addEventListener('DOMContentLoaded', function() {
        //Listen for click on collapsible elements
        var collapsible = document.getElementsByClassName('collapsible');
        for (var i = 0; i < collapsible.length; i++) {
            collapsible[i].addEventListener('click', collapse); 
        }
    });
}

// AJAX REQUESTS
// 'Get sentences'
function dataRequest(formData) {
    var request = new XMLHttpRequest();
    request.open('POST', '/fetch', true);

    request.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            
            const data = JSON.parse(request.responseText);
            document.getElementById('progress').setAttribute('hidden', true);
            document.getElementById('placeholder-text').setAttribute('hidden', true);
            showResults(data);
            
        }
        if (this.status == 410) {
            console.log("410 error");
        }

    };
    
    request.send(formData);
}

// Reload sentences
function reloadRequest(reloadData) {
    var request = new XMLHttpRequest();
    request.open('POST', '/reload', true);
    
    request.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            const data = JSON.parse(request.responseText);
            reloadResults(data)
        }
    };

    request.send(reloadData);
}

// FUNCTIONS
// Create, populate and display sentences table
function showResults(data) {
    
    //const resultsHead = document.querySelector('#results-table > thead');
    var form = document.getElementById('output');
    form.style.display = 'flex';
    const resultsBody = document.querySelector('#results-table > tbody');
    //Clear table
    while (resultsBody.firstChild) {
        resultsBody.removeChild(resultsBody.firstChild);
    }
    //Iterate across data and create output table
    for (var key in data) {    
        //Set row
        const tr = document.createElement('tr');
        //Add "word" column
        const word = document.createElement('td');
        word.textContent = key;
        tr.append(word);

        //Add "sentence" column
        const sentence = document.createElement('td'); 
        sentence.textContent = data[key]['sentence'];
        tr.append(sentence);

        //Add "translation" columnn or "placeholder" column
        length = Object.keys(data[key]).length;
        if (length == 3) {
            //Reveal translation header
            const head = document.getElementById('trans');
            head.classList.add('result-header');
            head.textContent = 'Translation';           
            //Add translation column
            const translation = document.createElement('td');
            translation.textContent = data[key]['translation'];
            tr.append(translation);
        }
        else {
            //Set empty translation header
            const head = document.getElementById('trans');
            //head.classList.add('out-col');
            head.textContent = '';
            
            const translation = document.createElement('td');
            translation.classList.add('empty-td');
            translation.textContent = '';
            tr.append(translation);
        }
        
        //Add "reload" checkboxes
        const check = document.createElement('input');
        check.setAttribute('type', 'checkbox');
        check.setAttribute('value', key);
        check.setAttribute('name', 'reload');
        const holder = document.createElement('td');
        holder.classList.add('checkbox');    
        holder.appendChild(check);
        tr.appendChild(holder);
        
        resultsBody.appendChild(tr);
    }
}

//Reload output table
function reloadResults(data) {
    
    //Iterate across response data
    for (var key in data) {
        //Get table
        const resultsBody = document.querySelector('#results-table > tbody');
        //Find row to reload
        for (var i = 0; i < resultsBody.rows.length; i++) {
            row = resultsBody.rows[i];
            if (row.cells[0].innerText == key) {
                //Reload example sentence
                row.cells[1].innerText = data[key]['sentence'];
                //Check if translation and change
                trans = data[key]['translation'];
                if ( trans != undefined) {
                    row.cells[2].innerText = trans;
                }
            }
        }
    }
}

//Make elements collapsible
function collapse() {
    var block = this.children[1];
    var header = this.children[0];
    var headerIcon = header.children[1];
    var headerTitle = header.children[0];

    if (block.style.maxHeight) {
        block.style.maxHeight = null;
        header.classList.remove('selected');
        headerIcon.innerText = '\u002B';
    }
    else {
        block.style.maxHeight = block.scrollHeight + 'px';
        header.classList.add('selected');
        headerIcon.innerText = '\u2212';
    }
}

//Output reload checkbox AJAX request
function reloadRequest(reloadData) {
    var request = new XMLHttpRequest();
    request.open('POST', '/reload', true);
    
    request.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            const data = JSON.parse(request.responseText);
            reloadResults(data)
        }
    };

    request.send(reloadData);
}

//Reload output table
function reloadResults(data) {
    
    //Iterate across response data
    for (var key in data) {
        //Get table
        const resultsBody = document.querySelector('#results-table > tbody');
        //Find row to reload
        for (var i = 0; i < resultsBody.rows.length; i++) {
            row = resultsBody.rows[i];
            if (row.cells[0].innerText == key) {
                //Reload example sentence
                row.cells[1].innerText = data[key]['sentence'];
                //Check if translation and change
                trans = data[key]['translation'];
                if ( trans != undefined) {
                    row.cells[2].innerText = trans;
                }
            }
        }
    }
}