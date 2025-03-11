from PIL import Image

def make_background_transparent_and_color_gold(input_path, output_path):
    # Open the image
    img = Image.open(input_path)
    
    # Convert to RGBA if it isn't already
    img = img.convert("RGBA")
    
    # Get the image data
    data = img.getdata()
    
    # Create a new list for the modified pixels
    new_data = []
    
    # Define what we consider "white" (allowing for some variation)
    white_threshold = 240
    # Define what we consider "black" (allowing for some variation)
    black_threshold = 50
    
    # Define our gold color (248, 175, 66)
    gold_color = (248, 175, 66, 255)
    
    for item in data:
        # If the pixel is "white" (all values close to 255)
        if item[0] >= white_threshold and item[1] >= white_threshold and item[2] >= white_threshold:
            # Make it transparent
            new_data.append((255, 255, 255, 0))
        # If the pixel is "black" or very dark (all values close to 0)
        elif item[0] <= black_threshold and item[1] <= black_threshold and item[2] <= black_threshold:
            # Make it gold
            new_data.append(gold_color)
        else:
            # Keep the original color
            new_data.append(item)
    
    # Update the image with the new data
    img.putdata(new_data)
    
    # Save the result
    img.save(output_path, "PNG")

if __name__ == "__main__":
    make_background_transparent_and_color_gold(
        "static/images/jaguar-logo.png",
        "static/images/jaguar-logo-transparent.png"
    )
