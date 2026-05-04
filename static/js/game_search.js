// TomSelect game search with Steam API lookup
var gameCache = {};

const gameSearch = new TomSelect('#game-search', {
    valueField: 'app_id',
    labelField: 'name',
    searchField: 'name',
    maxOptions: 20,
    placeholder: 'Search for a Steam game…',
    loadThrottle: 300,
    shouldLoad: function(query) {
        return query.length >= 2;
    },
    load: function(query, callback) {
        fetch('/api/games/search?q=' + encodeURIComponent(query))
            .then(response => response.json())
            .then(data => {
                data.forEach(function(g) { gameCache[g.app_id] = g; });
                callback(data);
            })
            .catch(function() {
                callback();
            });
    },
    render: {
        option: function(data, escape) {
            var img = data.capsule_image
                ? '<img src="' + escape(data.capsule_image) + '" alt="" class="me-2" style="width:46px;height:22px;object-fit:cover;border-radius:3px;vertical-align:middle;">'
                : '';
            var badge = data.has_review
                ? ' <span class="badge bg-warning text-dark ms-auto">Already reviewed</span>'
                : '';
            return '<div class="d-flex align-items-center py-1">' +
                img +
                '<span>' + escape(data.name) + '</span>' +
                badge +
                '</div>';
        },
        item: function(data, escape) {
            return '<span>' + escape(data.name) + '</span>';
        }
    },
    onChange: function(value) {
        if (value && gameCache[value]) {
            var g = gameCache[value];
            document.getElementById('app_id').value = value;
            document.getElementById('store').value = 'steam';
            document.getElementById('selected-game-name').textContent = g.name;
            document.getElementById('selected-game-image').src = g.header_image;
            document.getElementById('selected-game-appid').textContent = value;
            document.getElementById('game-selected').classList.remove('d-none');
        }
    }
});

// Handle clearing the game selection
document.getElementById('clear-game').addEventListener('click', function() {
    gameSearch.clear();
    document.getElementById('app_id').value = '';
    document.getElementById('store').value = 'steam';
    document.getElementById('game-selected').classList.add('d-none');
});
