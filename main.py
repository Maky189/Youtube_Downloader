from pytubefix import YouTube
from pytubefix.cli import on_progress
import os
import re
import subprocess

def download_video_and_audio(yt, title, output_path):
    try:
        if not isinstance(output_path, str):
            print("Error: Invalid output path.")
            return

        #List resolutions
        videos = yt.streams.filter(adaptive=True, file_extension="mp4", only_video=True).order_by("resolution").desc()
        audios = yt.streams.filter(adaptive=True, file_extension="mp4", only_audio=True).order_by("abr").desc()

        print("Select ID of the resolution: \n")
        for i in range(0, len(videos)):
            print(f"{i + 1}. Resolution: {videos[i].resolution}, FPS: {videos[i].fps}")

        print()

        option = 0
        try:
            option = int(input("Insert the ID of the resolution: "))
            if option == 0: raise ValueError
        except ValueError:
            print("\nYou have to insert the ID of the resolution:")
        
        # Get highest quality video and audio streams
        video = videos[option - 1]
        audio = audios[0]

        if not video or not audio:
            print("Error downloading video")
            return

        # Define temporary filenames
        video_file_name = f"{title}_video_temp.mp4"
        audio_file_name = f"{title}_audio_temp.mp4"
        final_file = os.path.join(output_path, f"{title}.mp4")
        

        # Print debug information
       

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

def main():
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
        title = re.sub(r'[\\/*?:"<>|]', "", yt.title)

        # Display video title
        print(f"\nVideo Title: {yt.title}")

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

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
