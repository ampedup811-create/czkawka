use crate::gui_data::GuiData;
use crate::help_functions::*;
use chrono::DateTime;
use gdk;
use gtk::prelude::*;
use gtk::{Align, Box as GtkBox, Button, Image, Label, Orientation, ScrolledWindow, Window, WindowPosition, WindowType};
use image::imageops::FilterType;
use image::GenericImageView;
use std::cell::RefCell;
use std::fs;
use std::path::Path;
use std::rc::Rc;

#[derive(Clone)]
pub struct ImageComparisonWindow {
    pub window: Window,
    pub images_box: GtkBox,
    pub button_delete: Button,
    pub button_save: Button,
    image_paths: Rc<RefCell<Vec<String>>>,
}

impl ImageComparisonWindow {
    pub fn new() -> Self {
        let window = Window::new(WindowType::Toplevel);
        window.set_title("Compare Images");
        window.set_default_size(850, 600);
        window.set_position(WindowPosition::Center);
        window.set_modal(false);

        let main_box = GtkBox::new(Orientation::Vertical, 5);
        main_box.set_margin_top(5);
        main_box.set_margin_bottom(5);
        main_box.set_margin_start(5);
        main_box.set_margin_end(5);

        // Scrolled window for images
        let scrolled_window = ScrolledWindow::new(gtk::NONE_ADJUSTMENT, gtk::NONE_ADJUSTMENT);
        scrolled_window.set_policy(gtk::PolicyType::Automatic, gtk::PolicyType::Automatic);
        scrolled_window.set_vexpand(true);

        // Box for images in grid layout
        let images_box = GtkBox::new(Orientation::Vertical, 10);
        images_box.set_margin_top(10);
        images_box.set_margin_bottom(10);
        images_box.set_margin_start(10);
        images_box.set_margin_end(10);

        scrolled_window.add(&images_box);
        main_box.pack_start(&scrolled_window, true, true, 0);

        // Button box at the bottom
        let button_box = GtkBox::new(Orientation::Horizontal, 5);
        button_box.set_margin_top(5);
        button_box.set_halign(Align::End);

        let button_delete = Button::with_label("Delete Selected");
        let button_save = Button::with_label("Save");

        button_box.pack_start(&button_delete, false, false, 0);
        button_box.pack_start(&button_save, false, false, 0);

        main_box.pack_start(&button_box, false, false, 0);

        window.add(&main_box);

        let image_paths = Rc::new(RefCell::new(Vec::new()));

        // Connect ESC key to close window
        let window_clone = window.clone();
        window.connect_key_press_event(move |_, event| {
            if event.keyval() == gdk::keys::constants::Escape {
                window_clone.close();
                return gtk::Inhibit(true);
            }
            gtk::Inhibit(false)
        });

        Self {
            window,
            images_box,
            button_delete,
            button_save,
            image_paths,
        }
    }

    pub fn show_images(&self, selected_paths: Vec<(String, String)>) {
        // Clear existing images
        for child in self.images_box.children() {
            self.images_box.remove(&child);
        }

        // Store paths for later use
        let mut paths = Vec::new();
        for (path, name) in &selected_paths {
            paths.push(format!("{}/{}", path, name));
        }
        *self.image_paths.borrow_mut() = paths;

        // Limit to 4 images
        let num_images = selected_paths.len().min(4);

        // Determine layout: 2x1 for 2 images, 2x2 for 3-4 images
        let num_cols = 2;

        let mut current_row_box: Option<GtkBox> = None;

        for (idx, (path, name)) in selected_paths.iter().take(num_images).enumerate() {
            // Create new row box if needed
            if idx % num_cols == 0 {
                let row_box = GtkBox::new(Orientation::Horizontal, 10);
                row_box.set_homogeneous(true);
                self.images_box.pack_start(&row_box, false, false, 0);
                current_row_box = Some(row_box);
            }

            if let Some(ref row_box) = current_row_box {
                let image_container = self.create_image_container(path, name);
                row_box.pack_start(&image_container, true, true, 0);
            }
        }

        self.images_box.show_all();
    }

    fn create_image_container(&self, path: &str, name: &str) -> GtkBox {
        let container = GtkBox::new(Orientation::Vertical, 5);
        container.set_margin_top(5);
        container.set_margin_bottom(5);
        container.set_margin_start(5);
        container.set_margin_end(5);

        let file_path = format!("{}/{}", path, name);

        // Image widget
        let image_widget = Image::new();

        // Load and scale image
        if let Ok(img) = image::open(&file_path) {
            let (width, height) = img.dimensions();

            // Calculate scaled dimensions (max 400x400 while preserving aspect ratio)
            let requested_dimensions = (400_u32, 400_u32);
            let new_size = if width > height {
                let new_width = requested_dimensions.0;
                let new_height = ((height as f32 / width as f32) * new_width as f32) as u32;
                (new_width.max(1), new_height.max(1))
            } else {
                let new_height = requested_dimensions.1;
                let new_width = ((width as f32 / height as f32) * new_height as f32) as u32;
                (new_width.max(1), new_height.max(1))
            };

            let img_resized = img.resize(new_size.0, new_size.1, FilterType::Triangle);

            // Save to temporary location and load into GTK Image
            if let Some(cache_dir) = Self::get_cache_dir() {
                if let Some(extension) = Path::new(&file_path).extension() {
                    let temp_file = cache_dir.join(format!("compare_{}.{}", std::process::id(), extension.to_string_lossy()));

                    if img_resized.save(&temp_file).is_ok() {
                        image_widget.set_from_file(&temp_file);
                        let _ = fs::remove_file(&temp_file);
                    }
                }
            }
        }

        container.pack_start(&image_widget, false, false, 0);

        // Metadata labels
        let metadata_box = GtkBox::new(Orientation::Vertical, 2);
        metadata_box.set_margin_top(5);

        // Filename
        let filename_label = Label::new(Some(&format!("Name: {}", name)));
        filename_label.set_line_wrap(true);
        filename_label.set_xalign(0.0);
        metadata_box.pack_start(&filename_label, false, false, 0);

        // Path
        let path_label = Label::new(Some(&format!("Path: {}", path)));
        path_label.set_line_wrap(true);
        path_label.set_xalign(0.0);
        metadata_box.pack_start(&path_label, false, false, 0);

        // Get file metadata
        if let Ok(metadata) = fs::metadata(&file_path) {
            // File size
            let size_bytes = metadata.len();
            let size_str = if size_bytes < 1024 {
                format!("{} B", size_bytes)
            } else if size_bytes < 1024 * 1024 {
                format!("{:.2} KB", size_bytes as f64 / 1024.0)
            } else {
                format!("{:.2} MB", size_bytes as f64 / (1024.0 * 1024.0))
            };
            let size_label = Label::new(Some(&format!("Size: {}", size_str)));
            size_label.set_xalign(0.0);
            metadata_box.pack_start(&size_label, false, false, 0);

            // Dimensions
            if let Ok(img) = image::open(&file_path) {
                let (width, height) = img.dimensions();
                let dimensions_label = Label::new(Some(&format!("Dimensions: {}x{}", width, height)));
                dimensions_label.set_xalign(0.0);
                metadata_box.pack_start(&dimensions_label, false, false, 0);
            }

            // Modified date
            if let Ok(modified) = metadata.modified() {
                if let Ok(datetime) = modified.duration_since(std::time::UNIX_EPOCH) {
                    let dt = DateTime::from_timestamp(datetime.as_secs() as i64, 0);
                    if let Some(dt) = dt {
                        let date_str = dt.format("%Y-%m-%d %H:%M:%S").to_string();
                        let modified_label = Label::new(Some(&format!("Modified: {}", date_str)));
                        modified_label.set_xalign(0.0);
                        metadata_box.pack_start(&modified_label, false, false, 0);
                    }
                }
            }
        }

        container.pack_start(&metadata_box, false, false, 0);

        container
    }

    fn get_cache_dir() -> Option<std::path::PathBuf> {
        use directories_next::ProjectDirs;
        if let Some(proj_dirs) = ProjectDirs::from("pl", "Qarmin", "Czkawka") {
            let cache_dir = proj_dirs.cache_dir().to_path_buf();
            if !cache_dir.exists() {
                let _ = fs::create_dir_all(&cache_dir);
            }
            Some(cache_dir)
        } else {
            None
        }
    }

    pub fn show_window(&self) {
        self.window.show_all();
    }

    pub fn connect_delete_button<F: Fn() + 'static>(&self, callback: F) {
        self.button_delete.connect_clicked(move |_| {
            callback();
        });
    }

    pub fn connect_save_button<F: Fn() + 'static>(&self, callback: F) {
        self.button_save.connect_clicked(move |_| {
            callback();
        });
    }

    pub fn get_image_paths(&self) -> Vec<String> {
        self.image_paths.borrow().clone()
    }
}

pub fn show_comparison_window_for_similar_images(gui_data: &GuiData) {
    let tree_view = &gui_data.main_notebook.tree_view_similar_images_finder;
    let (selected_rows, tree_model) = tree_view.selection().selected_rows();

    if selected_rows.len() < 2 || selected_rows.len() > 4 {
        // Show error message
        add_text_to_text_view(&gui_data.text_view_errors, "Please select 2 to 4 images to compare.");
        return;
    }

    let mut selected_paths = Vec::new();
    for tree_path in &selected_rows {
        if let Some(iter) = tree_model.iter(tree_path) {
            let path = tree_model.value(&iter, ColumnsSimilarImages::Path as i32).get::<String>().unwrap_or_default();
            let name = tree_model.value(&iter, ColumnsSimilarImages::Name as i32).get::<String>().unwrap_or_default();

            // Skip header rows
            let color = tree_model.value(&iter, ColumnsSimilarImages::Color as i32).get::<String>().unwrap_or_default();
            if color == HEADER_ROW_COLOR {
                continue;
            }

            selected_paths.push((path, name));
        }
    }

    if selected_paths.len() < 2 || selected_paths.len() > 4 {
        add_text_to_text_view(&gui_data.text_view_errors, "Please select 2 to 4 non-header images to compare.");
        return;
    }

    // Create and show comparison window
    let comparison_window = ImageComparisonWindow::new();
    comparison_window.show_images(selected_paths);

    // Connect delete button
    let gui_data_clone = gui_data.clone();
    let tree_view_clone = tree_view.clone();
    let window_clone = comparison_window.window.clone();
    comparison_window.connect_delete_button(move || {
        // TODO: Integrate with existing delete functionality from connect_button_delete.rs
        // For now, just close the window
        window_clone.close();
    });

    // Connect save button
    let gui_data_clone2 = gui_data.clone();
    comparison_window.connect_save_button(move || {
        // TODO: Integrate with existing save functionality from connect_button_save.rs
        // This would allow users to save the comparison results
    });

    comparison_window.show_window();
}
