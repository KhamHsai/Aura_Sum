/**
 * Alert utility tests.
 * SweetAlert2 is mocked so no real browser dialogs are opened.
 */
import { it, expect, vi, beforeEach } from 'vitest'

// Mock sweetalert2 before importing the utility
vi.mock('sweetalert2', () => ({
  default: {
    fire: vi.fn().mockResolvedValue({ isConfirmed: true }),
  },
}))

import Swal from 'sweetalert2'
import { showSuccessAlert, showErrorAlert, showDeleteConfirmation } from '../utils/alerts'

const mockFire = vi.mocked(Swal.fire)

beforeEach(() => {
  vi.clearAllMocks()
})

// 1. Uses sweetalert2 directly (not vue-sweetalert2)
it('imports Swal directly from sweetalert2 package', async () => {
  await showSuccessAlert('Done')
  expect(mockFire).toHaveBeenCalledOnce()
})

// 2. Success alert calls Swal.fire
it('showSuccessAlert calls Swal.fire with success icon', async () => {
  await showSuccessAlert('Great', 'All saved.')
  expect(mockFire).toHaveBeenCalledWith(
    expect.objectContaining({ icon: 'success', title: 'Great', text: 'All saved.' })
  )
})

// 3. Error alert calls Swal.fire
it('showErrorAlert calls Swal.fire with error icon', async () => {
  await showErrorAlert('Oops', 'Something failed.')
  expect(mockFire).toHaveBeenCalledWith(
    expect.objectContaining({ icon: 'error', title: 'Oops', text: 'Something failed.' })
  )
})

// 4. Confirmation uses warning icon
it('showDeleteConfirmation calls Swal.fire with warning icon', async () => {
  await showDeleteConfirmation({
    title: 'Delete?',
    text: 'Are you sure?',
    confirmButtonText: 'Yes',
    cancelButtonText: 'No',
  })
  expect(mockFire).toHaveBeenCalledWith(
    expect.objectContaining({ icon: 'warning' })
  )
})

// 5. Confirmation includes cancel button
it('showDeleteConfirmation enables the cancel button', async () => {
  await showDeleteConfirmation({
    title: 'Delete?',
    text: 'Are you sure?',
    confirmButtonText: 'Yes',
    cancelButtonText: 'No',
  })
  expect(mockFire).toHaveBeenCalledWith(
    expect.objectContaining({ showCancelButton: true, cancelButtonText: 'No' })
  )
})

// 6. Confirmation passes confirm button text
it('showDeleteConfirmation passes confirmButtonText', async () => {
  await showDeleteConfirmation({
    title: 'Delete?',
    text: 'Sure?',
    confirmButtonText: 'Delete it',
    cancelButtonText: 'Cancel',
  })
  expect(mockFire).toHaveBeenCalledWith(
    expect.objectContaining({ confirmButtonText: 'Delete it' })
  )
})

// 7. Success alert with no text still calls Swal.fire
it('showSuccessAlert works without text argument', async () => {
  await showSuccessAlert('Done')
  expect(mockFire).toHaveBeenCalledOnce()
  expect(mockFire).toHaveBeenCalledWith(
    expect.objectContaining({ icon: 'success', title: 'Done' })
  )
})
