🍎 ApplePrism - Multispectral Image Alignment and ARI Computation Application, Perfect for detailed spectral analysis

Project Description
ApplePrism is a comprehensive GUI-based Python application tailored for multispectral image processing and analysis. It automates the detection and loading of essential spectral channels—Green, RedEdge, NIR, and an RGB preview—from a selected folder. The application offers a dedicated manual alignment interface where users can fine-tune the relative positioning of the RedEdge and NIR channels (using intuitive arrow key controls) with respect to the Green channel. Once aligned, ApplePrism computes the ARI (a spectral index) and provides an interactive tool to select a region of interest (ROI) for calculating the average ARI value. This makes it an ideal tool for applications in precision agriculture, remote sensing, and environmental monitoring.

Key Features
✅ Multispectral Data Handling – Automatically identifies and loads required image channels (Green, RedEdge, NIR, and RGB) from a chosen folder.

✅ Interactive Manual Alignment – Enables precise adjustment of the RedEdge and NIR channels using keyboard controls (arrow keys with SHIFT modifier for NIR), with a real-time preview.

✅ ARI Index Computation – Calculates the ARI index from the aligned channels, normalizes the result, and presents it as a grayscale image.

✅ ROI Selection Tool – Offers an interactive canvas where users can draw a circular region to compute and display the average ARI value within the selected area.

✅ Futuristic UI Design – Built with tkinter and ttk, featuring a custom neon-inspired theme and modern styling for an engaging user experience.

Technologies Used
Python 3.x – The core programming language.

Tkinter & ttk – For constructing the graphical user interface with modern, themed widgets.

Pillow (PIL) – For image loading, resizing, and manipulation.

NumPy – For efficient numerical operations and array manipulations.

Tifffile – For reading multispectral TIFF images.

OS Module – For handling file system operations.
