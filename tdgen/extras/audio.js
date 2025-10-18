class AudioSection {
    constructor(audioSectionElement) {
        this.audioSectionElement = audioSectionElement;
        this.audioElement = this.audioSectionElement.querySelector('audio');
        this.segments = document.querySelectorAll('.segment');

        if (!this.audioElement) return;

        this.init();
    }

    init() {
        this.initSegment();
        this.initAudio();
    }

    initAudio() {
        this.audioElement.addEventListener('timeupdate', () => {
            const currentTime = this.audioElement.currentTime;

    initSegment() {
        for (const segment of this.segments) {
            segment.addEventListener('click', () => {
                var seconds = segment.getAttribute('data-start');
                this.audioElement.currentTime = seconds;
                this.audioElement.play();
            });
        }
    }
}

window.addEventListener("DOMContentLoaded", () => {
    for (const audioSection of document.querySelectorAll('.audio-section')) {
        new AudioSection(audioSection);
    }
});