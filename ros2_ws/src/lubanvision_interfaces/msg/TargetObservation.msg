# Detection state. Consumers must treat every state except DETECTED as
# non-actionable unless their own state machine explicitly permits it.
uint8 STATUS_NOT_VISIBLE=0
uint8 STATUS_DETECTED=1
uint8 STATUS_PARTIAL=2
uint8 STATUS_INVALID=3

# Timestamp and frame of the source camera image, not the publish time.
std_msgs/Header header

# ArUco marker ID. Set to -1 when no target is visible.
int32 target_id

# Detected marker center in image pixel coordinates.
float32 center_x_px
float32 center_y_px

# Center offset from the optical image center, in pixels.
# Positive X points right; positive Y points down.
float32 error_x_px
float32 error_y_px

# Pixel errors normalized by half the image width/height, normally [-1, 1].
float32 error_x_norm
float32 error_y_norm

# Marker quadrilateral area in square pixels and detector confidence [0, 1].
float32 area_px2
float32 confidence

uint8 status
