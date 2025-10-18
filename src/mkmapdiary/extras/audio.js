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
            var segments = Array.from(this.segments);
            segments.reverse();
            var found = false;
            for (const segment of segments) {
                var start = parseInt(segment.getAttribute('data-start'));
                if (currentTime >= start && !found) {
                    segment.classList.add('highlight');
                    found = true;
                } else {
                    segment.classList.remove('highlight');
                }
            }
        });
        this.audioElement.addEventListener('ended', () => {
            for (const segment of this.segments) {
                segment.classList.remove('highlight');
            }
        });
        this.audioElement.addEventListener('play', () => {
            this.stopOtherAudios();
        });
    }


    initSegment() {
        for (const segment of this.segments) {
            segment.addEventListener('click', () => {
                var seconds = segment.getAttribute('data-start');
                this.audioElement.currentTime = seconds;
                this.audioElement.play();
            });
        }
    }

    stopOtherAudios() {
        const audios = document.querySelectorAll('audio');
        for (const audio of audios) {
            if (audio !== this.audioElement) {
                audio.pause();
            }
        }
    }
}

window.addEventListener("DOMContentLoaded", () => {
    for (const audioSection of document.querySelectorAll('.audio-section')) {
        new AudioSection(audioSection);
    }
});