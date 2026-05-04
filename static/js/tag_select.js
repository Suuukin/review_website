// TomSelect tag selector with color picker
var colorPalette = ['#0d6efd', '#6c757d', '#198754', '#dc3545', '#ffc107', '#0dcaf0'];
var pendingNewTag = null;
var newTagsData = [];
var tagNameToColor = {};

var paletteContainer = document.getElementById('color-palette');
if (paletteContainer) {
    colorPalette.forEach(function(color) {
        var swatch = document.createElement('div');
        swatch.className = 'color-swatch';
        swatch.style.backgroundColor = color;
        swatch.dataset.color = color;
        swatch.addEventListener('click', function() {
            paletteContainer.querySelectorAll('.color-swatch').forEach(function(s) {
                s.classList.remove('selected');
            });
            swatch.classList.add('selected');
            selectColor(this.dataset.color);
        });
        paletteContainer.appendChild(swatch);
    });
}

function selectColor(color) {
    if (pendingNewTag) {
        var title = pendingNewTag;
        tagNameToColor[title] = color;
        updateNewTagsHidden();
        tagSelect.removeItem(title);
        addNewTagBadge(title, color);
        document.getElementById('new-tag-color-picker').classList.add('d-none');
        pendingNewTag = null;
    }
}

function addNewTagBadge(title, color) {
    var container = document.getElementById('new-tags-badges');
    if (!container) return;
    var badge = document.createElement('span');
    badge.className = 'new-tag-badge';
    badge.style.backgroundColor = color;
    badge.style.color = '#fff';
    badge.innerHTML = title + ' <span class="remove-new-tag" data-title="' + title.replace(/"/g, '&quot;') + '">&times;</span>';
    badge.querySelector('.remove-new-tag').addEventListener('click', function() {
        var t = this.dataset.title;
        newTagsData = newTagsData.filter(function(nt) { return nt.title !== t; });
        delete tagNameToColor[t];
        updateNewTagsHidden();
        this.parentElement.remove();
    });
    container.appendChild(badge);
}

function updateNewTagsHidden() {
    newTagsData = [];
    for (var title in tagNameToColor) {
        if (tagNameToColor.hasOwnProperty(title)) {
            newTagsData.push({title: title, color: tagNameToColor[title]});
        }
    }
    document.getElementById('new_tags').value = JSON.stringify(newTagsData);
}

const tagSelect = new TomSelect('#tags-input', {
    valueField: 'tag_id',
    labelField: 'title',
    searchField: 'title',
    maxOptions: 20,
    placeholder: 'Select or create tags...',
    persist: false,
    createOnBlur: true,
    openOnFocus: true,
    preload: 'focus',
    loadThrottle: 300,
    load: function(query, callback) {
        fetch('/api/tags/search?q=' + encodeURIComponent(query))
            .then(function(response) { return response.json(); })
            .then(function(data) { callback(data); })
            .catch(function() { callback(); });
    },
    create: function(input, callback) {
        callback({ tag_id: input, title: input, color: tagNameToColor[input] || '' });
    },
    render: {
        option: function(data, escape) {
            var color = data.color || '#4a6984';
            return '<div class="d-flex align-items-center py-1">' +
                '<span class="badge me-2" style="background-color:' + escape(color) + ';color:#fff;">' + escape(data.title) + '</span>' +
                '</div>';
        },
        item: function(data, escape) {
            var title = data.title || data.tag_id || '';
            var color = tagNameToColor[title] || data.color || '#4a6984';
            return '<span class="badge me-1" style="background-color:' + escape(color) + ';color:#fff;">' + escape(title) + '</span>';
        }
    },
    onOptionAdd: function(value) {
        document.getElementById('new-tag-name').textContent = value;
        document.getElementById('new-tag-color-picker').classList.remove('d-none');
        pendingNewTag = value;
    }
});
