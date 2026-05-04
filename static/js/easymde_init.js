// EasyMDE markdown editor initialization
const easyMDE = new EasyMDE({
    element: document.getElementById('content'),
    spellChecker: false,
    placeholder: 'Write your review in Markdown...',
    toolbar: [
        'bold', 'italic', 'heading', '|',
        'quote', 'unordered-list', 'ordered-list', '|',
        'code', 'table', '|',
        'guide'
    ],
    status: false,
});
