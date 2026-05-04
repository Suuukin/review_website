// Post type toggle — show/hide game search and title section
var typeRadios = document.querySelectorAll('input[name="post_type"]');
var gameSection = document.getElementById('game-search-section');
var titleSection = document.getElementById('title-section');

function togglePostType() {
    var isReview = document.getElementById('type-review').checked;
    if (isReview) {
        gameSection.style.display = 'block';
        titleSection.style.display = 'none';
        document.getElementById('store').value = 'steam';
    } else {
        gameSection.style.display = 'none';
        titleSection.style.display = 'block';
        gameSearch.clear();
        document.getElementById('app_id').value = '';
        document.getElementById('store').value = 'other';
        document.getElementById('game-selected').classList.add('d-none');
    }
}

typeRadios.forEach(function(r) {
    r.addEventListener('change', togglePostType);
});

// Ensure initial state matches the default checked radio
togglePostType();
