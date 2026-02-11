# noinspection PyInterpreter
from pytubefix import YouTube, Playlist
from pytubefix.cli import on_progress
import os
import re
import subprocess


def sanitize_title(title):
    """Sanitize a video title for use as a filename."""
    return re.sub(r'[\\/*?:"<>|]', "", title)


def download_AudioOnly(yt, title, output_path):
    try:
        if not os.path.isdir(output_path):
            os.makedirs(output_path, exist_ok=True)

        audio = yt.streams.get_audio_only()
        print("Downloading audio...")
        temp_filename = f"{title}_temp.{audio.subtype}"
        tmpPath = os.path.join(output_path, temp_filename)
        final_mp3 = os.path.join(output_path, f"{title}.mp3")

        # Download with complete filename including extension
        audio.download(output_path, filename=temp_filename)

        ffmpeg_command = [
            "ffmpeg", "-y", "-i", tmpPath, "-vn", "-ab", "192k", "-ar", "44100", "-f", "mp3", final_mp3
        ]
        subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(tmpPath)
        print("Audio downloaded.")

    except Exception as e:
        print(f"Occurred an Error: {e}")


def download_video_and_audio(yt, title, output_path, resolution_index=None):
    """Download video and audio streams separately, then merge with ffmpeg.
    
    Args:
        yt: YouTube object
        title: sanitized video title
        output_path: directory to save the final file
        resolution_index: if provided, skip the resolution prompt and use this index (0-based).
                          Use -1 for highest available resolution.
    """
    try:
        if not isinstance(output_path, str):
            print("Error: Invalid output path.")
            return

        if not os.path.isdir(output_path):
            os.makedirs(output_path, exist_ok=True)

        # List resolutions
        videos = yt.streams.filter(adaptive=True, file_extension="mp4", only_video=True).order_by("resolution").desc()
        audios = yt.streams.filter(adaptive=True, file_extension="mp4", only_audio=True).order_by("abr").desc()

        if resolution_index is None:
            # Interactive: let user pick resolution
            print("Select ID of the resolution: \n")
            for i in range(0, len(videos)):
                print(f"{i + 1}. Resolution: {videos[i].resolution}, FPS: {videos[i].fps}")

            print()

            option = 0
            try:
                option = int(input("Insert the ID of the resolution: "))
                if option == 0:
                    raise ValueError
            except ValueError:
                print("\nYou have to insert the ID of the resolution:")
                return

            video = videos[option - 1]
        elif resolution_index == -1:
            # Highest resolution (first in desc order)
            video = videos[0]
        else:
            video = videos[resolution_index]

        audio = audios[0]

        if not video or not audio:
            print("Error downloading video")
            return

        # Define temporary filenames
        video_file_name = f"{title}_video_temp.mp4"
        audio_file_name = f"{title}_audio_temp.mp4"
        final_file = os.path.join(output_path, f"{title}.mp4")

        # Download video and audio
        print("\nDownloading video...")
        video.download(output_path=output_path, filename=video_file_name)
        audio.download(output_path=output_path, filename=audio_file_name)

        # Merge video and audio using ffmpeg
        print("Saving Video...")
        video_file = os.path.join(output_path, video_file_name)
        audio_file = os.path.join(output_path, audio_file_name)
        ffmpeg_command = ["ffmpeg", "-y", "-i", video_file, "-i", audio_file, "-c", "copy", final_file]
        subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Clean up temporary files
        os.remove(video_file)
        os.remove(audio_file)

        print(f"Download completed: {final_file}")
    except Exception as e:
        print(f"An error occurred: {e}")


def handle_single_video():
    """Handle downloading a single YouTube video."""
    try:
        url = input("Url of the YouTube video: ").strip()
        try:
            yt = YouTube(url, on_progress_callback=on_progress)
        except Exception as e:
            print(f"Failed to fetch video details. Please check the URL. Error: {e}")
            return

        # Sanitize video title for file names
        if not yt.title:
            print("Error: Video title could not be retrieved.")
            return
        title = sanitize_title(yt.title)

        # Display video title
        print(f"\nVideo Title: {yt.title}")

        choise = int(input("Video or Audio?\nVideo: 1\nAudio: 2\nChoice: "))

        if choise == 1:
            # Check for subtitles
            if yt.captions:
                print("\nSubtitles available:")

                sub_choice = input("\nDo you wish to download the subtitles? (y/n): ").strip().lower()
                if sub_choice in ("y", "yes"):
                    available_subtitles = yt.captions
                    for i, subtitle in enumerate(available_subtitles, start=1):
                        print(f"{i}: {subtitle.code}")
                    try:
                        lang_choice = int(input("Choose the language (number): ")) - 1
                        if lang_choice < 0 or lang_choice >= len(available_subtitles):
                            print("Invalid choice. Please select a valid number.")
                            return
                        subtitle = list(available_subtitles)[lang_choice]
                        subtitle_path = os.path.join(os.path.expanduser("~/Videos"), f"{title}.srt")
                        subtitle.save_captions(subtitle_path)
                        print("Subtitle downloaded!")
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                        return

            # Set download path
            if os.name == "nt":
                path = os.path.join(os.path.expanduser("~"), "Videos")
            else:
                path = os.path.expanduser("~/Videos")

            # Download video and audio separately and merge them
            download_video_and_audio(yt, title, path)

        elif choise == 2:
            if os.name == "nt":
                path = os.path.join(os.path.expanduser("~"), "Music")
            else:
                path = os.path.expanduser("~/Music")

            download_AudioOnly(yt, title, path)

        else:
            print("Invalid input. Please enter a valid choice.")

    except Exception as e:
        print(f"An error occurred: {e}")


def handle_playlist():
    """Handle downloading an entire YouTube playlist."""
    try:
        url = input("Url of the YouTube playlist: ").strip()
        try:
            playlist = Playlist(url)
        except Exception as e:
            print(f"Failed to fetch playlist. Please check the URL. Error: {e}")
            return

        print(f"\nPlaylist Title: {playlist.title}")
        print(f"Number of videos: {len(playlist.videos)}")

        choise = int(input("\nVideo or Audio?\nVideo: 1\nAudio: 2\nChoice: "))

        if choise == 1:
            # Set download path inside a subfolder named after the playlist
            playlist_folder = sanitize_title(playlist.title)
            if os.name == "nt":
                base_path = os.path.join(os.path.expanduser("~"), "Videos")
            else:
                base_path = os.path.expanduser("~/Videos")
            path = os.path.join(base_path, playlist_folder)
            os.makedirs(path, exist_ok=True)

            # Ask for resolution preference once for the whole playlist
            print("\nResolution options for playlist:")
            print("1. Highest available resolution for each video")
            print("2. Choose resolution for the first video (applied to all)")
            res_choice = int(input("Choice: "))

            resolution_index = None
            if res_choice == 1:
                resolution_index = -1  # highest
            elif res_choice == 2:
                # Show resolution options from the first video
                first_yt = playlist.videos[0]
                videos_streams = first_yt.streams.filter(
                    adaptive=True, file_extension="mp4", only_video=True
                ).order_by("resolution").desc()

                print("\nSelect ID of the resolution:\n")
                for i in range(len(videos_streams)):
                    print(f"{i + 1}. Resolution: {videos_streams[i].resolution}, FPS: {videos_streams[i].fps}")
                print()

                option = int(input("Insert the ID of the resolution: "))
                if option <= 0:
                    print("Invalid choice.")
                    return
                resolution_index = option - 1
            else:
                print("Invalid choice.")
                return

            for i, yt in enumerate(playlist.videos, start=1):
                try:
                    title = sanitize_title(yt.title)
                    print(f"\n[{i}/{len(playlist.videos)}] {yt.title}")
                    yt.register_on_progress_callback(on_progress)
                    download_video_and_audio(yt, title, path, resolution_index=resolution_index)
                except Exception as e:
                    print(f"Error downloading '{yt.title}': {e}")
                    continue

            print(f"\nPlaylist download completed! Files saved to: {path}")

        elif choise == 2:
            # Set download path inside a subfolder named after the playlist
            playlist_folder = sanitize_title(playlist.title)
            if os.name == "nt":
                base_path = os.path.join(os.path.expanduser("~"), "Music")
            else:
                base_path = os.path.expanduser("~/Music")
            path = os.path.join(base_path, playlist_folder)
            os.makedirs(path, exist_ok=True)

            for i, yt in enumerate(playlist.videos, start=1):
                try:
                    title = sanitize_title(yt.title)
                    print(f"\n[{i}/{len(playlist.videos)}] {yt.title}")
                    yt.register_on_progress_callback(on_progress)
                    download_AudioOnly(yt, title, path)
                except Exception as e:
                    print(f"Error downloading '{yt.title}': {e}")
                    continue

            print(f"\nPlaylist download completed! Files saved to: {path}")

        else:
            print("Invalid input. Please enter a valid choice.")

    except Exception as e:
        print(f"An error occurred: {e}")


def main():
    print("=== YouTube Downloader ===\n")
    print("1. Single Video")
    print("2. Playlist")

    try:
        mode = int(input("\nChoice: "))
    except ValueError:
        print("Invalid input. Please enter a number.")
        return

    if mode == 1:
        handle_single_video()
    elif mode == 2:
        handle_playlist()
    else:
        print("Invalid choice. Please enter 1 or 2.")


if __name__ == "__main__":
    main()
