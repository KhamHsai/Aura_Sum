/**
 * Small reusable SweetAlert2 helpers.
 * Import Swal directly — no vue-sweetalert2 plugin needed.
 */
import Swal from 'sweetalert2'

export function showSuccessAlert(title: string, text?: string) {
  return Swal.fire({
    icon: 'success',
    title,
    text,
    confirmButtonText: 'OK',
  })
}

export function showErrorAlert(title: string, text?: string) {
  return Swal.fire({
    icon: 'error',
    title,
    text,
    confirmButtonText: 'OK',
  })
}

export function showDeleteConfirmation(options: {
  title: string
  text: string
  confirmButtonText: string
  cancelButtonText: string
}) {
  return Swal.fire({
    icon: 'warning',
    title: options.title,
    text: options.text,
    showCancelButton: true,
    confirmButtonText: options.confirmButtonText,
    cancelButtonText: options.cancelButtonText,
    focusCancel: true,
  })
}
